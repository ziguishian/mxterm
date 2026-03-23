from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

from mxterm.constants import COMMON_TOOLS
from mxterm.models import EnvironmentSummary

POSIX_BUILTINS = {
    "alias",
    "bg",
    "cd",
    "echo",
    "eval",
    "exec",
    "exit",
    "export",
    "fg",
    "jobs",
    "pwd",
    "readonly",
    "set",
    "shift",
    "source",
    "test",
    "times",
    "trap",
    "type",
    "ulimit",
    "umask",
    "unset",
}

POWERSHELL_BUILTINS = {
    "cd",
    "chdir",
    "clear",
    "cls",
    "copy-item",
    "dir",
    "echo",
    "get-childitem",
    "get-location",
    "ls",
    "move-item",
    "ni",
    "new-item",
    "pwd",
    "remove-item",
    "ren",
    "rename-item",
    "ri",
    "set-location",
}


def detect_os_name() -> str:
    raw = platform.system().lower()
    if raw.startswith("darwin"):
        return "macos"
    if raw.startswith("windows"):
        return "windows"
    return "linux"


def path_style(os_name: str) -> str:
    return "windows" if os_name == "windows" else "posix"


def current_shell_name(explicit_shell: str | None = None) -> str:
    if explicit_shell and explicit_shell != "auto":
        return explicit_shell.lower()
    shell_env = os.environ.get("SHELL", "")
    if shell_env:
        name = Path(shell_env).name.lower()
        if "zsh" in name:
            return "zsh"
        if "bash" in name:
            return "bash"
    if os.name == "nt":
        return "powershell"
    return "bash"


def shell_executable(shell_name: str) -> str | None:
    if shell_name == "zsh":
        return shutil.which("zsh")
    if shell_name == "bash":
        return shutil.which("bash")
    if shell_name == "powershell":
        return shutil.which("pwsh") or shutil.which("powershell")
    return None


def _powershell_probe(token: str) -> bool:
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if not shell:
        return token.lower() in POWERSHELL_BUILTINS
    command = [
        shell,
        "-NoProfile",
        "-Command",
        f"if (Get-Command '{token}' -ErrorAction SilentlyContinue) {{ exit 0 }} else {{ exit 1 }}",
    ]
    result = subprocess.run(command, capture_output=True, check=False)
    return result.returncode == 0 or token.lower() in POWERSHELL_BUILTINS


def command_exists(token: str, shell_name: str) -> bool:
    if not token:
        return False
    lowered = token.lower()
    if shell_name in {"zsh", "bash"} and lowered in POSIX_BUILTINS:
        return True
    if shell_name == "powershell" and _powershell_probe(lowered):
        return True
    if token.startswith("./") or token.startswith("../") or token.startswith("/") or token.startswith(".\\") or token.startswith("..\\"):
        return Path(token).exists()
    if Path(token).exists():
        return True
    return shutil.which(token) is not None


def discover_tools() -> list[str]:
    return [tool for tool in COMMON_TOOLS if shutil.which(tool)]


def environment_summary(cwd: str, shell_name: str) -> EnvironmentSummary:
    os_name = detect_os_name()
    return EnvironmentSummary(
        os_name=os_name,
        shell=shell_name,
        path_style=path_style(os_name),
        cwd=cwd,
        available_tools=discover_tools(),
    )
