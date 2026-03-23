from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from platformdirs import PlatformDirs

from mxterm.config.defaults import default_config, default_config_text
from mxterm.constants import APP_NAME
from mxterm.models import AgentSettings, ContextSettings, MXTermConfig, OllamaSettings, SafetySettings, ShellSettings, UISettings


def get_dirs() -> PlatformDirs:
    return PlatformDirs(appname=APP_NAME, appauthor=False)


def config_dir() -> Path:
    return Path(get_dirs().user_config_dir)


def data_dir() -> Path:
    return Path(get_dirs().user_data_dir)


def state_dir() -> Path:
    return Path(get_dirs().user_state_dir)


def cache_dir() -> Path:
    return Path(get_dirs().user_cache_dir)


def config_path(explicit_path: Path | None = None) -> Path:
    return explicit_path or config_dir() / "config.toml"


def session_path() -> Path:
    return state_dir() / "session.json"


def hooks_dir() -> Path:
    return data_dir() / "hooks"


def logs_dir() -> Path:
    return state_dir() / "logs"


def ensure_runtime_dirs() -> None:
    for path in (config_dir(), data_dir(), state_dir(), cache_dir(), hooks_dir(), logs_dir()):
        path.mkdir(parents=True, exist_ok=True)


def init_config_file(destination: Path | None = None, overwrite: bool = False) -> Path:
    ensure_runtime_dirs()
    target = config_path(destination)
    if target.exists() and not overwrite:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(default_config_text(), encoding="utf-8")
    return target


def _merge_config(data: dict[str, Any]) -> MXTermConfig:
    defaults = default_config()
    ollama = data.get("ollama", {})
    shell = data.get("shell", {})
    safety = data.get("safety", {})
    ui = data.get("ui", {})
    context = data.get("context", {})
    agent = data.get("agent", {})
    return MXTermConfig(
        ollama=OllamaSettings(
            host=str(ollama.get("host", defaults.ollama.host)),
            model=str(ollama.get("model", defaults.ollama.model)),
            timeout_seconds=int(ollama.get("timeout_seconds", defaults.ollama.timeout_seconds)),
        ),
        shell=ShellSettings(
            preferred=str(shell.get("preferred", defaults.shell.preferred)),
            confirm_mode=str(shell.get("confirm_mode", defaults.shell.confirm_mode)),
            auto_capture=bool(shell.get("auto_capture", defaults.shell.auto_capture)),
            auto_capture_mode=str(shell.get("auto_capture_mode", defaults.shell.auto_capture_mode)),
            explicit_command=str(shell.get("explicit_command", defaults.shell.explicit_command)),
            show_banner=bool(shell.get("show_banner", defaults.shell.show_banner)),
        ),
        safety=SafetySettings(
            dry_run=bool(safety.get("dry_run", defaults.safety.dry_run)),
            block_high_risk=bool(safety.get("block_high_risk", defaults.safety.block_high_risk)),
            preview_ai_commands=bool(safety.get("preview_ai_commands", defaults.safety.preview_ai_commands)),
            permission_level=str(safety.get("permission_level", defaults.safety.permission_level)),
        ),
        ui=UISettings(
            theme=str(ui.get("theme", defaults.ui.theme)),
            show_welcome=bool(ui.get("show_welcome", defaults.ui.show_welcome)),
            show_explanations=bool(ui.get("show_explanations", defaults.ui.show_explanations)),
        ),
        context=ContextSettings(
            history_limit=int(context.get("history_limit", defaults.context.history_limit)),
        ),
        agent=AgentSettings(
            enabled=bool(agent.get("enabled", defaults.agent.enabled)),
            max_steps=int(agent.get("max_steps", defaults.agent.max_steps)),
            preflight_checks=bool(agent.get("preflight_checks", defaults.agent.preflight_checks)),
            confirm_each_step=bool(agent.get("confirm_each_step", defaults.agent.confirm_each_step)),
            retry_on_failure=bool(agent.get("retry_on_failure", defaults.agent.retry_on_failure)),
            max_retries=int(agent.get("max_retries", defaults.agent.max_retries)),
        ),
    )


def load_config(explicit_path: Path | None = None) -> MXTermConfig:
    path = config_path(explicit_path)
    if not path.exists():
        return default_config()
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    return _merge_config(raw)


def load_session_data() -> dict[str, Any]:
    path = session_path()
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def save_session_data(data: dict[str, Any]) -> None:
    ensure_runtime_dirs()
    session_path().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _toml_literal(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def save_config(config: MXTermConfig, explicit_path: Path | None = None) -> Path:
    ensure_runtime_dirs()
    target = config_path(explicit_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = config.to_dict()
    sections = [
        "ollama",
        "shell",
        "safety",
        "ui",
        "context",
        "agent",
    ]
    lines: list[str] = []
    for section in sections:
        section_data = data.get(section, {})
        lines.append(f"[{section}]")
        for key, value in section_data.items():
            lines.append(f"{key} = {_toml_literal(value)}")
        lines.append("")
    target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return target
