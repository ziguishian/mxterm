from __future__ import annotations

from dataclasses import asdict
import json
import shutil
import sys
from pathlib import Path
import os

import typer
from rich.prompt import Confirm

from mxterm import __version__
from mxterm.agent.executor import execute_agent_plan
from mxterm.ai.ollama_client import OllamaClient
from mxterm.config.loader import (
    cache_dir,
    config_dir,
    config_path,
    data_dir,
    ensure_runtime_dirs,
    hooks_dir,
    init_config_file,
    load_config,
    logs_dir,
    save_config,
    session_path,
    state_dir,
)
from mxterm.context.session import load_session, record_failure, reset_session, save_session
from mxterm.installer.bootstrap import generate_hook_file, render_hook_template
from mxterm.installer.profiles import default_profile_path, hook_file_path, profile_has_mxterm_block, resolve_shell_name, install_shell_hook, uninstall_shell_hook
from mxterm.models import DoctorCheck
from mxterm.routing.classifier import classify_input
from mxterm.routing.pipeline import MXTermPipeline
from mxterm.shell.adapters import join_input_tokens
from mxterm.shell.capabilities import current_shell_name, detect_os_name, shell_executable
from mxterm.shell.executor import run_shell_code
from mxterm.ui.console import stderr_console
from mxterm.ui.renderers import (
    render_decision,
    render_doctor,
    render_agent_execution,
    render_help_overview,
    render_history,
    render_hook_preview,
    render_model_list,
    render_runtime_paths,
    render_session,
)
from mxterm.utils.logging import clear_logs, log_event, log_path, tail_logs

app = typer.Typer(help="MXTerm shell enhancement tool.", no_args_is_help=True)
config_app = typer.Typer(help="Manage MXTerm configuration.")
logs_app = typer.Typer(help="Inspect MXTerm logs.")
hooks_app = typer.Typer(help="Inspect and refresh generated shell hooks.")
model_app = typer.Typer(help="Inspect and switch Ollama models used by MXTerm.")
permission_app = typer.Typer(help="Inspect and switch MXTerm execution permission levels.")
app.add_typer(config_app, name="config")
app.add_typer(logs_app, name="logs")
app.add_typer(hooks_app, name="hooks")
app.add_typer(model_app, name="model")
app.add_typer(permission_app, name="permission")


def _pipeline() -> MXTermPipeline:
    return MXTermPipeline(load_config())


def _echo_process_text(text: str, *, err: bool = False) -> None:
    stream = sys.stderr if err else sys.stdout
    encoding = getattr(stream, "encoding", None) or "utf-8"
    safe_text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
    typer.echo(safe_text, nl=False, err=err)


def _normalize_permission_level(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"low", "medium", "high"}:
        raise typer.BadParameter("Permission level must be one of: low, medium, high.")
    return normalized


def _hook_session_checks(target_shell: str | None = None) -> list[DoctorCheck]:
    active = os.environ.get("MXTERM_HOOK_ACTIVE") == "1"
    session_shell = os.environ.get("MXTERM_HOOK_SHELL", "unknown")
    auto_capture = os.environ.get("MXTERM_HOOK_AUTO_CAPTURE", "unknown")
    auto_capture_mode = os.environ.get("MXTERM_HOOK_AUTO_CAPTURE_MODE", "unknown")
    explicit_command = os.environ.get("MXTERM_HOOK_EXPLICIT_COMMAND", "unknown")
    enter_handler = os.environ.get("MXTERM_HOOK_ENTER_HANDLER", "unknown")

    details = (
        "Run `mxterm install --shell ...` and restart or reload the shell profile."
        if not active
        else f"shell={session_shell}, auto_capture={auto_capture}, mode={auto_capture_mode}, command={explicit_command}, enter_handler={enter_handler}"
    )
    checks = [DoctorCheck("Current Session Hook Active", active, details)]
    if target_shell:
        checks.append(
            DoctorCheck(
                "Current Session Matches Target Shell",
                active and session_shell == target_shell,
                f"target={target_shell}, session={session_shell}",
            )
        )
        if target_shell == "powershell":
            checks.append(
                DoctorCheck(
                    "PowerShell Enter Handler Active",
                    active and enter_handler == "1",
                    f"enter_handler={enter_handler}",
                )
            )
    return checks


def _doctor_checks() -> list[DoctorCheck]:
    ensure_runtime_dirs()
    config = load_config()
    client = OllamaClient(config.ollama.host, timeout_seconds=config.ollama.timeout_seconds)
    reachable, detail = client.ping()
    mxterm_on_path = shutil.which("mxterm")
    pipx_on_path = shutil.which("pipx")
    active_shell = current_shell_name(config.shell.preferred)
    active_shell_executable = shell_executable(active_shell)
    checks = [
        DoctorCheck("Config", True, f"Using {config_path()}"),
        DoctorCheck("Platform", True, f"{detect_os_name()} / default shell {active_shell}"),
        DoctorCheck("MXTerm CLI", mxterm_on_path is not None, mxterm_on_path or "mxterm is not on PATH yet."),
        DoctorCheck("pipx", pipx_on_path is not None, pipx_on_path or "pipx not found on PATH."),
        DoctorCheck("Shell Binary", active_shell_executable is not None, active_shell_executable or f"{active_shell} not found on PATH."),
        DoctorCheck("Hooks Directory", hooks_dir().exists(), f"{hooks_dir()}"),
        DoctorCheck("Active Hook File", hook_file_path(active_shell).exists(), f"{hook_file_path(active_shell)}"),
        DoctorCheck("Ollama API", reachable, detail),
    ]
    checks.extend(_hook_session_checks(active_shell))
    if reachable:
        try:
            models = client.list_models()
        except Exception as exc:  # pragma: no cover
            checks.append(DoctorCheck("Ollama Models", False, str(exc)))
        else:
            model_ok = config.ollama.model in models
            checks.append(
                DoctorCheck(
                    "Ollama Model",
                    model_ok,
                    f"Configured model {config.ollama.model} {'found' if model_ok else 'missing'}. Installed: {', '.join(models) or 'none'}",
                )
            )
    return checks


@app.command()
def version() -> None:
    """Print the MXTerm version."""
    typer.echo(__version__)


@app.command()
def doctor(
    as_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a rich table."),
) -> None:
    """Inspect the local MXTerm environment."""
    checks = _doctor_checks()
    if as_json:
        typer.echo(json.dumps([asdict(check) for check in checks], ensure_ascii=False))
        return
    render_doctor(checks)


@app.command("help")
def help_command() -> None:
    """Show a practical MXTerm usage guide."""
    ensure_runtime_dirs()
    render_help_overview(load_config())


def _write_config(
    path: Path | None = typer.Option(None, help="Optional custom config path."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite an existing config file."),
) -> None:
    target = init_config_file(path, overwrite=overwrite)
    typer.echo(f"Initialized config at {target}")


@config_app.command("init")
def config_init(
    path: Path | None = typer.Option(None, help="Optional custom config path."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite an existing config file."),
) -> None:
    """Create a default MXTerm config."""
    _write_config(path, overwrite)


@config_app.command("path")
def config_show_path() -> None:
    """Print the active config path."""
    ensure_runtime_dirs()
    typer.echo(config_path())


@config_app.command("show")
def config_show(as_json: bool = typer.Option(False, "--json", help="Emit JSON.")) -> None:
    """Print the active MXTerm config."""
    ensure_runtime_dirs()
    config = load_config()
    if as_json:
        typer.echo(json.dumps(config.to_dict(), ensure_ascii=False, indent=2))
        return
    typer.echo(json.dumps(config.to_dict(), ensure_ascii=False, indent=2))


@app.command("config-init")
def config_init_legacy(
    path: Path | None = typer.Option(None, help="Optional custom config path."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite an existing config file."),
) -> None:
    """Legacy alias for `mxterm config init`."""
    _write_config(path, overwrite)


@app.command()
def install(
    shell: str = typer.Option("auto", help="Target shell: auto, zsh, bash, or powershell."),
    profile: Path | None = typer.Option(None, help="Optional shell profile path."),
) -> None:
    """Install MXTerm hooks into a shell profile."""
    ensure_runtime_dirs()
    init_config_file()
    shell_name = resolve_shell_name(shell)
    generate_hook_file(shell_name, config=load_config())
    result = install_shell_hook(shell_name, profile)
    typer.echo(result.message)


@app.command()
def uninstall(
    shell: str = typer.Option("auto", help="Target shell: auto, zsh, bash, or powershell."),
    profile: Path | None = typer.Option(None, help="Optional shell profile path."),
) -> None:
    """Remove MXTerm hooks from a shell profile."""
    shell_name = resolve_shell_name(shell)
    result = uninstall_shell_hook(shell_name, profile)
    typer.echo(result.message)


@app.command()
def resolve(
    input_text: str = typer.Option(..., "--input", help="Raw user input."),
    shell: str = typer.Option("auto", help="Shell name."),
    cwd: str = typer.Option(".", help="Current working directory."),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON only."),
) -> None:
    """Resolve a line of user input into MXTerm routing output."""
    shell_name = resolve_shell_name(shell)
    decision = _pipeline().resolve(user_input=input_text, shell_name=shell_name, cwd=str(Path(cwd).resolve()))
    if as_json:
        typer.echo(json.dumps(decision.to_dict(), ensure_ascii=False))
        return
    render_decision(decision)
    log_event("resolve", {"decision": decision, "cwd": cwd, "shell": shell_name})


@app.command()
def explain(
    input_text: str = typer.Option(..., "--input", help="Natural-language input."),
    shell: str = typer.Option("auto", help="Shell name."),
    cwd: str = typer.Option(".", help="Current working directory."),
) -> None:
    """Preview what MXTerm would do without executing it."""
    shell_name = resolve_shell_name(shell)
    decision = _pipeline().resolve(user_input=input_text, shell_name=shell_name, cwd=str(Path(cwd).resolve()))
    render_decision(decision)
    log_event("explain", {"decision": decision, "cwd": cwd, "shell": shell_name})


@app.command()
def run(
    input_text: str = typer.Option(..., "--input", help="Command or natural-language input."),
    shell: str = typer.Option("auto", help="Shell name."),
    cwd: str = typer.Option(".", help="Current working directory."),
    yes: bool = typer.Option(False, "--yes", help="Execute without interactive confirmation when allowed."),
) -> None:
    """Resolve input and optionally execute it in a subprocess."""
    shell_name = resolve_shell_name(shell)
    resolved_cwd = str(Path(cwd).resolve())
    decision = _pipeline().resolve(user_input=input_text, shell_name=shell_name, cwd=resolved_cwd)
    render_decision(decision)
    log_event("run.preview", {"decision": decision, "cwd": resolved_cwd, "shell": shell_name})

    if decision.route == "block":
        raise typer.Exit(code=1)
    if decision.dry_run:
        typer.echo("Dry-run mode is enabled. Command was not executed.")
        raise typer.Exit(code=0)
    if not decision.shell_code:
        typer.echo("No executable shell code was produced.")
        raise typer.Exit(code=1)

    config = load_config()
    permission_level = config.safety.permission_level.lower()

    if decision.source == "agent" and decision.steps:
        if permission_level != "low" and decision.requires_confirmation and not yes:
            if not Confirm.ask("Start this agent plan now?", default=False):
                raise typer.Exit(code=1)

        def confirm_step(index, step, current_step_cwd, rendered_command):
            if yes or permission_level == "high":
                return True
            if permission_level == "low":
                prompt = f"Execute step {index} in {current_step_cwd}? {rendered_command}"
                return Confirm.ask(prompt, default=False)
            if not config.agent.confirm_each_step or len(decision.steps) <= 1:
                return True
            prompt = f"Execute step {index} in {current_step_cwd}? {rendered_command}"
            return Confirm.ask(prompt, default=False)

        execution = execute_agent_plan(
            shell_name,
            decision.steps,
            resolved_cwd,
            preflight_checks=config.agent.preflight_checks,
            retry_on_failure=config.agent.retry_on_failure,
            max_retries=config.agent.max_retries,
            confirm_callback=confirm_step,
        )
        render_agent_execution(execution)
        for step_result in execution.step_results:
            if step_result.stdout:
                _echo_process_text(step_result.stdout)
            if step_result.stderr:
                _echo_process_text(step_result.stderr, err=True)
        if not execution.ok:
            session_state = load_session(resolved_cwd)
            record_failure(session_state, execution.message, config.context.history_limit)
            save_session(session_state)
        log_event(
            "run.agent_execute",
            {
                "decision": decision,
                "cwd": resolved_cwd,
                "shell": shell_name,
                "execution": execution,
            },
        )
        raise typer.Exit(code=0 if execution.ok else 1)

    if decision.requires_confirmation and not yes:
        if not Confirm.ask("Execute this command now?", default=False):
            raise typer.Exit(code=1)

    result = run_shell_code(shell_name, decision.shell_code, resolved_cwd)
    if result.stdout:
        _echo_process_text(result.stdout)
    if result.stderr:
        _echo_process_text(result.stderr, err=True)
    if result.returncode != 0:
        session_state = load_session(resolved_cwd)
        record_failure(session_state, f"Command failed ({result.returncode}): {decision.display_command}", config.context.history_limit)
        save_session(session_state)
    log_event(
        "run.execute",
        {
            "decision": decision,
            "cwd": resolved_cwd,
            "shell": shell_name,
            "returncode": result.returncode,
        },
    )
    raise typer.Exit(code=result.returncode)


@app.command("self-update")
def self_update() -> None:
    """Print the recommended upgrade command."""
    typer.echo("Use `pipx upgrade mxterm` to upgrade MXTerm.")


@model_app.command("list")
def model_list() -> None:
    """List installed Ollama models and highlight the configured one."""
    config = load_config()
    client = OllamaClient(config.ollama.host, timeout_seconds=config.ollama.timeout_seconds)
    try:
        models = client.list_models()
    except Exception as exc:
        typer.echo(f"Could not list Ollama models: {exc}")
        raise typer.Exit(code=1)
    render_model_list(models, config.ollama.model)


@model_app.command("current")
def model_current() -> None:
    """Print the currently configured Ollama model."""
    config = load_config()
    typer.echo(config.ollama.model)


@model_app.command("use")
def model_use(
    model_name: str = typer.Argument(..., help="Installed Ollama model name to configure."),
    force: bool = typer.Option(False, "--force", help="Save the model name even if Ollama does not currently report it."),
) -> None:
    """Switch the configured Ollama model in MXTerm."""
    ensure_runtime_dirs()
    config = load_config()
    client = OllamaClient(config.ollama.host, timeout_seconds=config.ollama.timeout_seconds)
    try:
        available_models = client.list_models()
    except Exception as exc:
        if not force:
            typer.echo(f"Could not query Ollama models: {exc}")
            raise typer.Exit(code=1)
        available_models = []
    if not force and model_name not in available_models:
        typer.echo(
            f"Model {model_name} is not installed in Ollama. Available: {', '.join(available_models) or 'none'}"
        )
        raise typer.Exit(code=1)
    config.ollama.model = model_name
    path = save_config(config)
    typer.echo(f"Configured MXTerm to use model {model_name} in {path}")


@permission_app.command("current")
def permission_current() -> None:
    """Print the current MXTerm permission level."""
    config = load_config()
    typer.echo(config.safety.permission_level)


@permission_app.command("use")
def permission_use(
    level: str = typer.Argument(..., help="Permission level: low, medium, or high."),
) -> None:
    """Switch MXTerm execution permission level."""
    ensure_runtime_dirs()
    config = load_config()
    normalized = _normalize_permission_level(level)
    config.safety.permission_level = normalized
    path = save_config(config)
    typer.echo(f"Configured MXTerm permission level to {normalized} in {path}")


@app.command()
def history() -> None:
    """Show recent MXTerm commands and failures."""
    ensure_runtime_dirs()
    session = load_session()
    render_history(session)


@app.command()
def session() -> None:
    """Show the current MXTerm session summary."""
    ensure_runtime_dirs()
    render_session(load_session())


@app.command("reset-session")
def reset_session_command() -> None:
    """Reset the MXTerm session history and cwd snapshot."""
    ensure_runtime_dirs()
    session = reset_session()
    render_session(session)


@app.command()
def runtime() -> None:
    """Show important MXTerm runtime paths."""
    ensure_runtime_dirs()
    render_runtime_paths(
        {
            "config_dir": config_dir(),
            "data_dir": data_dir(),
            "state_dir": state_dir(),
            "cache_dir": cache_dir(),
            "hooks_dir": hooks_dir(),
            "logs_dir": logs_dir(),
            "session_file": session_path(),
            "log_file": log_path(),
        }
    )


@hooks_app.command("refresh")
def hooks_refresh(
    shell: str = typer.Option("auto", help="Target shell: auto, zsh, bash, or powershell."),
) -> None:
    """Regenerate the shell hook file from the current MXTerm config."""
    ensure_runtime_dirs()
    shell_name = resolve_shell_name(shell)
    target = generate_hook_file(shell_name, config=load_config())
    typer.echo(f"Refreshed hook file at {target}")


@hooks_app.command("path")
def hooks_path_command(
    shell: str = typer.Option("auto", help="Target shell: auto, zsh, bash, or powershell."),
) -> None:
    """Print the generated shell hook path."""
    typer.echo(hook_file_path(resolve_shell_name(shell)))


@hooks_app.command("show")
def hooks_show(
    shell: str = typer.Option("auto", help="Target shell: auto, zsh, bash, or powershell."),
) -> None:
    """Print the rendered hook content for the current config."""
    ensure_runtime_dirs()
    shell_name = resolve_shell_name(shell)
    typer.echo(render_hook_template(shell_name, config=load_config()), nl=False)


@hooks_app.command("doctor")
def hooks_doctor(
    shell: str = typer.Option("auto", help="Target shell: auto, zsh, bash, or powershell."),
    profile: Path | None = typer.Option(None, help="Optional shell profile path."),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a rich table."),
) -> None:
    """Inspect the generated hook file and target shell profile."""
    ensure_runtime_dirs()
    shell_name = resolve_shell_name(shell)
    profile_path = (profile or default_profile_path(shell_name)).expanduser().resolve()
    hook_path = hook_file_path(shell_name)
    rendered = render_hook_template(shell_name, config=load_config())
    on_disk = hook_path.read_text(encoding="utf-8") if hook_path.exists() else ""
    checks = [
        DoctorCheck("Profile Path", profile_path.exists(), str(profile_path)),
        DoctorCheck("Profile Contains MXTerm", profile_has_mxterm_block(profile_path), str(profile_path)),
        DoctorCheck("Hook File Exists", hook_path.exists(), str(hook_path)),
        DoctorCheck("Hook Up To Date", hook_path.exists() and on_disk == rendered, str(hook_path)),
    ]
    checks.extend(_hook_session_checks(shell_name))
    if as_json:
        typer.echo(json.dumps([asdict(check) for check in checks], ensure_ascii=False))
        return
    render_doctor(checks)


@logs_app.command("path")
def logs_path_command() -> None:
    """Print the MXTerm log file path."""
    typer.echo(log_path())


@logs_app.command("tail")
def logs_tail(
    lines: int = typer.Option(20, "--lines", "-n", help="How many log lines to show."),
) -> None:
    """Show recent MXTerm log entries."""
    entries = tail_logs(lines)
    if not entries:
        typer.echo("No log entries yet.")
        return
    for line in entries:
        typer.echo(line)


@logs_app.command("clear")
def logs_clear() -> None:
    """Clear the MXTerm log file."""
    path = clear_logs()
    typer.echo(f"Cleared logs at {path}")


@app.command("hook-dispatch", hidden=True)
def hook_dispatch(
    shell: str = typer.Option(..., help="Shell name."),
    cwd: str = typer.Option(".", help="Current working directory."),
    args: list[str] = typer.Argument(None),
) -> None:
    """Internal command used by shell hooks."""
    shell_name = resolve_shell_name(shell)
    raw_input = join_input_tokens(args or [])
    config = load_config()
    classification = classify_input(raw_input, shell_name)
    pipeline = MXTermPipeline(config)
    if classification == "natural_language":
        with stderr_console.status(
            f"[bold #46c2cb]MXTerm[/bold #46c2cb] [dim]translating with[/dim] [bold white]{config.ollama.model}[/bold white] [dim]...[/dim]",
            spinner="dots2",
            spinner_style="cyan",
        ):
            decision = pipeline.resolve(user_input=raw_input, shell_name=shell_name, cwd=str(Path(cwd).resolve()))
    else:
        decision = pipeline.resolve(user_input=raw_input, shell_name=shell_name, cwd=str(Path(cwd).resolve()))
    render_hook_preview(decision, model_name=config.ollama.model if decision.source in {"ai", "agent"} else None)

    if decision.route == "block":
        raise typer.Exit(code=1)

    if decision.dry_run:
        raise typer.Exit(code=0)

    if decision.requires_confirmation:
        if not Confirm.ask("Execute this command?", default=False):
            raise typer.Exit(code=1)

    if decision.shell_code:
        sys.stdout.write(decision.shell_code)
    log_event("hook.dispatch", {"decision": decision, "cwd": cwd, "shell": shell_name})


def main() -> None:
    app()


if __name__ == "__main__":
    main()
