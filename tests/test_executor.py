import os
from pathlib import Path

from mxterm.shell.executor import run_shell_code


def test_run_shell_code_for_direct_command():
    if os.name == "nt":
        result = run_shell_code("powershell", "Write-Output 'mxterm-ok'", str(Path.cwd()))
    else:
        result = run_shell_code("bash", "printf 'mxterm-ok\\n'", str(Path.cwd()))
    assert result.returncode == 0
    assert "mxterm-ok" in result.stdout
