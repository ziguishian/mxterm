from __future__ import annotations

from pathlib import Path

from rich.panel import Panel
from rich.table import Table

from mxterm.models import AgentExecutionResult, DoctorCheck, MXTermConfig, RouteDecision, SessionContext
from mxterm.ui.console import console, stderr_console


ACCENT = "#46c2cb"


def _decision_tone(decision: RouteDecision) -> tuple[str, str, str]:
    if decision.route == "block":
        if "Please enter another request" in decision.message or "Please enter another request" in decision.explanation:
            return ("warning", "yellow3", "MXTerm Warning")
        return ("failure", "red", "MXTerm Failed")
    if decision.route == "suggest_fix" or decision.requires_confirmation or decision.risk in {"medium", "high"}:
        return ("warning", "yellow3", "MXTerm Warning")
    return ("success", "green3", "MXTerm Success")


def _status_line(decision: RouteDecision) -> str:
    _, color, label = _decision_tone(decision)
    return f"[bold {color}]o[/bold {color}] [bold {color}]{label}[/bold {color}] [dim]|[/dim] {decision.message}"


def _hook_preview_lines(decision: RouteDecision, model_name: str | None = None) -> list[str]:
    tone, _, _ = _decision_tone(decision)
    lines = [_status_line(decision)]

    detail_parts: list[str] = []
    if model_name and decision.source in {"ai", "agent"}:
        detail_parts.append(f"[bold {ACCENT}]model[/bold {ACCENT}] {model_name}")
    if decision.display_command:
        detail_parts.append(f"[bold {ACCENT}]command[/bold {ACCENT}] {decision.display_command}")
    if detail_parts:
        lines.append("[dim]" + "  |  ".join(detail_parts) + "[/dim]")

    if tone == "success":
        if decision.plan_summary:
            lines.append(f"[dim]{decision.plan_summary}[/dim]")
        if decision.explanation:
            lines.append(f"[dim]{decision.intent}[/dim]")
        return lines

    lines.append(f"[bold {ACCENT}]input[/bold {ACCENT}] {decision.original_input}")
    if decision.plan_summary:
        lines.append(f"[bold {ACCENT}]plan[/bold {ACCENT}] {decision.plan_summary}")
    if decision.explanation:
        lines.append(f"[bold {ACCENT}]intent[/bold {ACCENT}] {decision.intent} [dim]|[/dim] {decision.explanation}")
    if decision.preview_summary:
        lines.append(f"[bold yellow3]preview[/bold yellow3] {decision.preview_summary}")
    if decision.preview_items:
        for item in decision.preview_items:
            lines.append(f"[dim]  - {item}[/dim]")
    if not decision.display_command and decision.source in {"ai", "agent"}:
        lines.append("[bold yellow3]warning[/bold yellow3] no executable command returned. Please enter another request.")
    if decision.risk_reasons:
        lines.append(f"[bold {ACCENT}]reasons[/bold {ACCENT}] {'; '.join(decision.risk_reasons)}")
    return lines


def render_banner() -> None:
    console.print(
        Panel.fit(
            f"[bold {ACCENT}]MXTerm[/bold {ACCENT}]\nCross-platform shell enhancement powered by Ollama.",
            border_style=ACCENT,
        )
    )


def render_doctor(checks: list[DoctorCheck]) -> None:
    table = Table(title="MXTerm Doctor")
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Detail")
    for check in checks:
        status = "[green]OK[/green]" if check.ok else "[red]FAIL[/red]"
        table.add_row(check.name, status, check.detail)
    console.print(table)


def render_history(session: SessionContext) -> None:
    commands = Table(title="MXTerm History")
    commands.add_column("Recent Commands", style="bold cyan")
    commands.add_column("Recent Failures", style="bold red")
    max_rows = max(len(session.recent_commands), len(session.recent_failures), 1)
    for index in range(max_rows):
        left = session.recent_commands[index] if index < len(session.recent_commands) else ""
        right = session.recent_failures[index] if index < len(session.recent_failures) else ""
        commands.add_row(left, right)
    console.print(commands)


def render_session(session: SessionContext) -> None:
    body = [
        f"[bold]Current directory:[/bold] {session.cwd}",
        f"[bold]Recent commands:[/bold] {len(session.recent_commands)}",
        f"[bold]Recent failures:[/bold] {len(session.recent_failures)}",
    ]
    console.print(Panel("\n".join(body), title="MXTerm Session", border_style="green"))


def render_runtime_paths(paths: dict[str, Path]) -> None:
    table = Table(title="MXTerm Runtime Paths")
    table.add_column("Name", style="bold")
    table.add_column("Path")
    for name, path in paths.items():
        table.add_row(name, str(path))
    console.print(table)


def render_decision(decision: RouteDecision) -> None:
    _, color, label = _decision_tone(decision)
    body = [
        _status_line(decision),
        f"[bold]Input:[/bold] {decision.original_input}",
        f"[bold]Route:[/bold] {decision.route}",
        f"[bold]Source:[/bold] {decision.source}",
        f"[bold]Intent:[/bold] {decision.intent}",
        f"[bold]Risk:[/bold] {decision.risk}",
        f"[bold]Dry run:[/bold] {decision.dry_run}",
        f"[bold]Steps:[/bold] {len(decision.steps)}",
        f"[bold]Command:[/bold] {decision.display_command or '-'}",
    ]
    if decision.plan_summary:
        body.append(f"[bold]Plan:[/bold] {decision.plan_summary}")
    if decision.explanation:
        body.append(f"[bold]Explanation:[/bold] {decision.explanation}")
    if decision.preview_summary:
        body.append(f"[bold yellow3]Preview:[/bold yellow3] {decision.preview_summary}")
    if decision.preview_items:
        body.append(f"[bold]Targets:[/bold] {'; '.join(decision.preview_items)}")
    if decision.risk_reasons:
        body.append(f"[bold]Risk reasons:[/bold] {'; '.join(decision.risk_reasons)}")
    console.print(Panel("\n".join(body), title=label, border_style=color))


def render_hook_preview(decision: RouteDecision, model_name: str | None = None) -> None:
    for line in _hook_preview_lines(decision, model_name=model_name):
        stderr_console.print(line)


def render_help_overview(config: MXTermConfig) -> None:
    body = [
        "[bold]What you can do with MXTerm[/bold]",
        "",
        "1. Run normal shell commands directly, such as `git status` or `Get-ChildItem`.",
        "2. Type natural language, such as `查看当前目录下的文件夹` or `install dependencies for this project`.",
        "3. Ask MXTerm to plan multi-step work, such as `先检查项目结构，再安装依赖，最后启动它`.",
        "4. Preview risky actions before execution, especially delete or overwrite tasks.",
        "",
        f"[bold]Current model:[/bold] {config.ollama.model}",
        f"[bold]Explicit AI command:[/bold] {config.shell.explicit_command}",
        f"[bold]Permission level:[/bold] {config.safety.permission_level}",
        "",
        "[bold]Useful commands[/bold]",
        "- `mxterm doctor` to check Ollama, hooks, and shell integration",
        "- `mxterm model list` to see installed Ollama models",
        "- `mxterm model current` to show the active model",
        "- `mxterm model use <name>` to switch the configured model",
        "- `mxterm permission use low|medium|high` to control confirmation strictness",
        "- `mxterm hooks doctor --shell powershell` to verify the current shell session",
        "- `mxterm history` and `mxterm session` to inspect recent activity",
        "",
        "[bold]Examples[/bold]",
        "- `mx 查看当前目录下的文件夹`",
        "- `mx 删除 logs 目录下 7 天前的文件`",
        "- `mxterm explain --shell powershell --cwd . --input \"先检查项目结构，再安装依赖，最后启动它\"`",
    ]
    console.print(Panel("\n".join(body), title="MXTerm Help", border_style=ACCENT))


def render_model_list(models: list[str], configured_model: str) -> None:
    table = Table(title="MXTerm Models")
    table.add_column("Model", style="bold")
    table.add_column("Configured")
    if not models:
        table.add_row("(no models found)", "No")
        console.print(table)
        return
    for model in models:
        configured = "[green]Yes[/green]" if model == configured_model else ""
        table.add_row(model, configured)
    console.print(table)


def render_agent_execution(result: AgentExecutionResult) -> None:
    if result.preflight_checks:
        preflight = Table(title="MXTerm Agent Preflight")
        preflight.add_column("Check", style="bold")
        preflight.add_column("Status")
        preflight.add_column("Detail")
        for check in result.preflight_checks:
            status = "[green]OK[/green]" if check.ok else "[red]FAIL[/red]"
            preflight.add_row(check.name, status, check.detail)
        console.print(preflight)

    if result.step_results:
        steps = Table(title="MXTerm Agent Steps")
        steps.add_column("Step", style="bold")
        steps.add_column("Type")
        steps.add_column("Attempts")
        steps.add_column("Status")
        steps.add_column("Command / Message")
        for step in result.step_results:
            status = "[green]OK[/green]" if step.ok else "[red]FAIL[/red]"
            detail = step.command if step.command else step.message
            steps.add_row(str(step.step_index), step.step_type, str(step.attempts), status, detail)
        console.print(steps)

    tone = "green3" if result.ok else "red"
    title = "MXTerm Agent Success" if result.ok else "MXTerm Agent Failed"
    console.print(
        Panel(
            "\n".join(
                [
                    f"[bold]Message:[/bold] {result.message}",
                    f"[bold]Final cwd:[/bold] {result.final_cwd}",
                ]
            ),
            title=title,
            border_style=tone,
        )
    )
