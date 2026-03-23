from pathlib import Path
from subprocess import CompletedProcess

from mxterm.installer.profiles import default_profile_path, install_shell_hook, uninstall_shell_hook


def test_install_and_uninstall_profile_block(tmp_path, monkeypatch):
    profile = tmp_path / ".zshrc"
    hook_dir = tmp_path / "hooks"
    monkeypatch.setattr("mxterm.installer.profiles.hooks_dir", lambda: hook_dir)
    result = install_shell_hook("zsh", profile)
    assert result.changed is True
    assert "MXTerm" in profile.read_text(encoding="utf-8")

    uninstall_result = uninstall_shell_hook("zsh", profile)
    assert uninstall_result.changed is True
    assert "MXTerm" not in profile.read_text(encoding="utf-8")


def test_default_profile_path_prefers_powershell_reported_profile(monkeypatch):
    monkeypatch.setattr("mxterm.installer.profiles.detect_os_name", lambda: "windows")
    monkeypatch.setattr("mxterm.installer.profiles.shell_executable", lambda shell_name: "powershell.exe")
    monkeypatch.setattr(
        "mxterm.installer.profiles.subprocess.run",
        lambda *args, **kwargs: CompletedProcess(args=args[0], returncode=0, stdout="D:\\system\\documents\\WindowsPowerShell\\Microsoft.PowerShell_profile.ps1\n", stderr=""),
    )

    path = default_profile_path("powershell")

    assert path == Path("D:/system/documents/WindowsPowerShell/Microsoft.PowerShell_profile.ps1")
