from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from mxterm.config.loader import hooks_dir
from mxterm.constants import PROFILE_MARKER_END, PROFILE_MARKER_START
from mxterm.shell.capabilities import current_shell_name, detect_os_name, shell_executable


@dataclass(slots=True)
class InstallResult:
    changed: bool
    profile_path: Path
    message: str


def profile_has_mxterm_block(profile_path: Path) -> bool:
    if not profile_path.exists():
        return False
    content = profile_path.read_text(encoding="utf-8")
    return PROFILE_MARKER_START in content and PROFILE_MARKER_END in content


def resolve_shell_name(shell: str) -> str:
    resolved = current_shell_name() if shell == "auto" else shell.lower()
    if resolved not in {"zsh", "bash", "powershell"}:
        raise ValueError(f"Unsupported shell: {shell}")
    return resolved


def _probe_powershell_profile_path() -> Path | None:
    executable = shell_executable("powershell")
    if not executable:
        return None
    command = [
        executable,
        "-NoProfile",
        "-Command",
        "$PROFILE.CurrentUserCurrentHost",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError:
        return None
    if result.returncode != 0:
        return None
    raw = result.stdout.strip()
    if not raw:
        return None
    return Path(raw).expanduser()


def default_profile_path(shell_name: str) -> Path:
    home = Path.home()
    os_name = detect_os_name()
    if shell_name == "zsh":
        return home / ".zshrc"
    if shell_name == "bash":
        bashrc = home / ".bashrc"
        if bashrc.exists() or os_name != "macos":
            return bashrc
        return home / ".bash_profile"
    if shell_name == "powershell":
        if os_name == "windows":
            probed = _probe_powershell_profile_path()
            if probed:
                return probed
            documents = Path(os.environ.get("USERPROFILE", str(home))) / "Documents"
            pwsh_profile = documents / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
            if pwsh_profile.parent.exists() or not (documents / "WindowsPowerShell").exists():
                return pwsh_profile
            return documents / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1"
        return home / ".config" / "powershell" / "Microsoft.PowerShell_profile.ps1"
    raise ValueError(f"Unsupported shell: {shell_name}")


def _profile_block(shell_name: str, hook_path: Path) -> str:
    if shell_name == "powershell":
        source_line = f'. "{hook_path}"'
    else:
        source_line = f'[ -f "{hook_path}" ] && . "{hook_path}"'
    return f"{PROFILE_MARKER_START}\n{source_line}\n{PROFILE_MARKER_END}\n"


def hook_file_path(shell_name: str) -> Path:
    suffix = ".ps1" if shell_name == "powershell" else ".sh"
    return hooks_dir() / f"{shell_name}{suffix}"


def install_shell_hook(shell_name: str, profile: Path | None = None) -> InstallResult:
    hooks_dir().mkdir(parents=True, exist_ok=True)
    profile_path = (profile or default_profile_path(shell_name)).expanduser().resolve()
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path = hook_file_path(shell_name)
    block = _profile_block(shell_name, hook_path)
    existing = profile_path.read_text(encoding="utf-8") if profile_path.exists() else ""
    if PROFILE_MARKER_START in existing and PROFILE_MARKER_END in existing:
        return InstallResult(False, profile_path, f"MXTerm is already installed in {profile_path}")
    if profile_path.exists():
        backup_path = profile_path.with_suffix(profile_path.suffix + ".mxterm.bak")
        backup_path.write_text(existing, encoding="utf-8")
    profile_path.write_text(existing.rstrip() + ("\n\n" if existing.strip() else "") + block, encoding="utf-8")
    return InstallResult(True, profile_path, f"Installed MXTerm hook into {profile_path}")


def uninstall_shell_hook(shell_name: str, profile: Path | None = None) -> InstallResult:
    profile_path = (profile or default_profile_path(shell_name)).expanduser().resolve()
    if not profile_path.exists():
        return InstallResult(False, profile_path, f"Profile does not exist: {profile_path}")
    existing = profile_path.read_text(encoding="utf-8")
    start = existing.find(PROFILE_MARKER_START)
    end = existing.find(PROFILE_MARKER_END)
    if start == -1 or end == -1:
        return InstallResult(False, profile_path, f"MXTerm block not found in {profile_path}")
    end += len(PROFILE_MARKER_END)
    new_content = (existing[:start] + existing[end:]).strip()
    profile_path.write_text((new_content + "\n") if new_content else "", encoding="utf-8")
    return InstallResult(True, profile_path, f"Removed MXTerm hook from {profile_path}")
