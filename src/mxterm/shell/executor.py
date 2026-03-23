from __future__ import annotations

import os
import subprocess


def run_shell_code(shell_name: str, shell_code: str, cwd: str) -> subprocess.CompletedProcess[str]:
    if shell_name == "powershell":
        shell = "pwsh" if shutil_which("pwsh") else "powershell"
        utf8_prefix = (
            "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
            "$OutputEncoding = [Console]::OutputEncoding; "
        )
        command = [shell, "-NoProfile", "-Command", utf8_prefix + shell_code]
        return subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    else:
        shell = os.environ.get("SHELL") or ("/bin/zsh" if shell_name == "zsh" else "/bin/bash")
        command = [shell, "-lc", shell_code]
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, errors="replace", check=False)


def shutil_which(name: str) -> str | None:
    for path in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(path, name)
        if os.path.isfile(candidate):
            return candidate
        if os.name == "nt":
            exe = candidate + ".exe"
            if os.path.isfile(exe):
                return exe
    return None
