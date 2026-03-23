from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Callable

from mxterm.models import AgentExecutionResult, AgentPreflightCheck, AgentStepResult, TranslationStep
from mxterm.shell.adapters import render_steps
from mxterm.shell.capabilities import command_exists
from mxterm.shell.executor import run_shell_code

STEP_CONFIRM_CALLBACK = Callable[[int, TranslationStep, str, str], bool]


def resolve_step_path(path: str, current_cwd: str) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        return str(candidate)
    return str(Path(current_cwd, path).resolve())


def _split_first_segment(command: str) -> str:
    return re.split(r"\s*(?:&&|\|\||;|\|)\s*", command.strip(), maxsplit=1)[0].strip()


def _first_command_token(shell_name: str, command: str) -> str | None:
    segment = _split_first_segment(command)
    if not segment:
        return None
    try:
        tokens = shlex.split(segment, posix=shell_name != "powershell")
    except ValueError:
        tokens = segment.split()
    while tokens and tokens[0] in {"&"}:
        tokens.pop(0)
    if not tokens:
        return None
    head = tokens[0]
    if head.startswith("$") or head.startswith("("):
        return None
    return head


def build_preflight_checks(shell_name: str, steps: list[TranslationStep], cwd: str) -> list[AgentPreflightCheck]:
    checks: list[AgentPreflightCheck] = []
    current_cwd = cwd
    for index, step in enumerate(steps, start=1):
        if step.type == "chdir" and step.path:
            target = resolve_step_path(step.path, current_cwd)
            ok = Path(target).exists() and Path(target).is_dir()
            detail = f"step {index}: directory {'ready' if ok else 'missing'} -> {target}"
            checks.append(AgentPreflightCheck(name=f"Step {index} directory", ok=ok, detail=detail))
            if ok:
                current_cwd = target
            continue
        if step.type == "shell" and step.command:
            token = _first_command_token(shell_name, step.command)
            if token is None:
                checks.append(
                    AgentPreflightCheck(
                        name=f"Step {index} command",
                        ok=True,
                        detail=f"step {index}: skipped local availability probe for `{step.command}`",
                    )
                )
                continue
            ok = command_exists(token, shell_name)
            detail = f"step {index}: command {'found' if ok else 'missing'} -> {token}"
            checks.append(AgentPreflightCheck(name=f"Step {index} command", ok=ok, detail=detail))
    return checks


def execute_agent_plan(
    shell_name: str,
    steps: list[TranslationStep],
    cwd: str,
    *,
    preflight_checks: bool = True,
    retry_on_failure: bool = True,
    max_retries: int = 1,
    confirm_callback: STEP_CONFIRM_CALLBACK | None = None,
) -> AgentExecutionResult:
    current_cwd = str(Path(cwd).resolve())
    checks = build_preflight_checks(shell_name, steps, current_cwd) if preflight_checks else []
    if any(not check.ok for check in checks):
        return AgentExecutionResult(
            ok=False,
            final_cwd=current_cwd,
            preflight_checks=checks,
            message="Agent preflight checks failed. Fix the missing dependency or path and try again.",
        )

    if not steps:
        return AgentExecutionResult(
            ok=False,
            final_cwd=current_cwd,
            preflight_checks=checks,
            message="No executable agent steps were available.",
        )

    results: list[AgentStepResult] = []
    for index, step in enumerate(steps, start=1):
        rendered = render_steps(shell_name, [step])
        if confirm_callback and not confirm_callback(index, step, current_cwd, rendered):
            return AgentExecutionResult(
                ok=False,
                final_cwd=current_cwd,
                preflight_checks=checks,
                step_results=results,
                message=f"Execution cancelled before step {index}.",
            )

        if step.type == "chdir" and step.path:
            target = resolve_step_path(step.path, current_cwd)
            target_path = Path(target)
            ok = target_path.exists() and target_path.is_dir()
            current_cwd = target if ok else current_cwd
            results.append(
                AgentStepResult(
                    step_index=index,
                    step_type=step.type,
                    command=rendered,
                    cwd=target if ok else current_cwd,
                    attempts=1,
                    returncode=0 if ok else 1,
                    ok=ok,
                    message="Changed working directory." if ok else f"Directory does not exist: {target}",
                    next_cwd=current_cwd,
                )
            )
            if not ok:
                return AgentExecutionResult(
                    ok=False,
                    final_cwd=current_cwd,
                    preflight_checks=checks,
                    step_results=results,
                    message=f"Agent step {index} failed while changing directory.",
                )
            continue

        attempts = 0
        final_result: AgentStepResult | None = None
        while True:
            attempts += 1
            completed = run_shell_code(shell_name, rendered, current_cwd)
            final_result = AgentStepResult(
                step_index=index,
                step_type=step.type,
                command=rendered,
                cwd=current_cwd,
                attempts=attempts,
                returncode=completed.returncode,
                ok=completed.returncode == 0,
                stdout=completed.stdout,
                stderr=completed.stderr,
                message="Command completed." if completed.returncode == 0 else "Command failed.",
                next_cwd=current_cwd,
            )
            if final_result.ok:
                break
            if not retry_on_failure or attempts > max_retries:
                break
        results.append(final_result)
        if not final_result.ok:
            return AgentExecutionResult(
                ok=False,
                final_cwd=current_cwd,
                preflight_checks=checks,
                step_results=results,
                message=f"Agent step {index} failed after {final_result.attempts} attempt(s).",
            )

    return AgentExecutionResult(
        ok=True,
        final_cwd=current_cwd,
        preflight_checks=checks,
        step_results=results,
        message=f"Executed {len(results)} agent step(s).",
    )
