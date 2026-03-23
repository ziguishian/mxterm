from __future__ import annotations

import re
from importlib import resources
from pathlib import Path

from mxterm.config.loader import hooks_dir
from mxterm.config.loader import load_config
from mxterm.installer.profiles import hook_file_path
from mxterm.models import MXTermConfig


def load_hook_template(shell_name: str) -> str:
    filename = {"zsh": "zsh.sh", "bash": "bash.sh", "powershell": "powershell.ps1"}[shell_name]
    local_path = Path(__file__).resolve().parent.parent / "hooks" / filename
    if local_path.exists():
        return local_path.read_text(encoding="utf-8")
    return resources.files("mxterm.hooks").joinpath(filename).read_text(encoding="utf-8")


def _sanitize_command_name(raw: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", raw.strip())
    if not cleaned:
        return "mx"
    if not re.match(r"^[A-Za-z_]", cleaned):
        cleaned = f"mx_{cleaned}"
    return cleaned


def _normalize_auto_capture_mode(raw: str) -> str:
    normalized = raw.strip().lower()
    if normalized in {"always", "smart", "natural_language"}:
        return normalized
    return "smart"


def render_hook_template(shell_name: str, config: MXTermConfig | None = None) -> str:
    resolved_config = config or load_config()
    template = load_hook_template(shell_name)
    replacements = {
        "__MXTERM_EXPLICIT_COMMAND__": _sanitize_command_name(resolved_config.shell.explicit_command),
        "__MXTERM_AUTO_CAPTURE__": "1" if resolved_config.shell.auto_capture else "0",
        "__MXTERM_AUTO_CAPTURE_MODE__": _normalize_auto_capture_mode(resolved_config.shell.auto_capture_mode),
        "__MXTERM_SHOW_BANNER__": "1" if resolved_config.shell.show_banner else "0",
        "__MXTERM_MODEL__": resolved_config.ollama.model,
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    return template


def generate_hook_file(shell_name: str, config: MXTermConfig | None = None) -> Path:
    hooks_dir().mkdir(parents=True, exist_ok=True)
    target = hook_file_path(shell_name)
    target.write_text(render_hook_template(shell_name, config=config), encoding="utf-8")
    return target
