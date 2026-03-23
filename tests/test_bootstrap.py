from mxterm.config.defaults import default_config
from mxterm.installer.bootstrap import generate_hook_file


def test_generate_hook_file(tmp_path, monkeypatch):
    monkeypatch.setattr("mxterm.installer.bootstrap.hooks_dir", lambda: tmp_path)
    monkeypatch.setattr("mxterm.installer.profiles.hooks_dir", lambda: tmp_path)
    path = generate_hook_file("bash")
    content = path.read_text(encoding="utf-8")
    assert path.exists()
    assert "command_not_found_handle" in content
    assert "bind -x" in content


def test_generate_zsh_hook_file_contains_accept_line_widget(tmp_path, monkeypatch):
    monkeypatch.setattr("mxterm.installer.bootstrap.hooks_dir", lambda: tmp_path)
    monkeypatch.setattr("mxterm.installer.profiles.hooks_dir", lambda: tmp_path)
    path = generate_hook_file("zsh")
    content = path.read_text(encoding="utf-8")
    assert path.exists()
    assert "zle -N __mxterm_accept_line" in content
    assert "bindkey '^M' __mxterm_accept_line" in content


def test_generate_hook_file_uses_configured_command_name(tmp_path, monkeypatch):
    monkeypatch.setattr("mxterm.installer.bootstrap.hooks_dir", lambda: tmp_path)
    monkeypatch.setattr("mxterm.installer.profiles.hooks_dir", lambda: tmp_path)
    config = default_config()
    config.shell.explicit_command = "askmx"
    config.shell.auto_capture = False
    config.shell.auto_capture_mode = "always"
    config.shell.show_banner = False
    path = generate_hook_file("bash", config=config)
    content = path.read_text(encoding="utf-8")
    assert "askmx()" in content
    assert "__MXTERM_EXPLICIT_COMMAND__" not in content
    assert "__MXTERM_AUTO_CAPTURE__" not in content
    assert "__MXTERM_AUTO_CAPTURE_MODE__" not in content


def test_generate_hook_file_exports_session_markers(tmp_path, monkeypatch):
    monkeypatch.setattr("mxterm.installer.bootstrap.hooks_dir", lambda: tmp_path)
    monkeypatch.setattr("mxterm.installer.profiles.hooks_dir", lambda: tmp_path)
    path = generate_hook_file("powershell")
    content = path.read_text(encoding="utf-8")
    assert '$env:MXTERM_HOOK_ACTIVE = "1"' in content
    assert '$env:MXTERM_HOOK_SHELL = "powershell"' in content
    assert '$env:MXTERM_HOOK_ENTER_HANDLER = "0"' in content
    assert '$env:MXTERM_HOOK_MODEL = "qwen3:8b"' in content
    assert "Test-MXTermShouldAutoCapture" in content
    assert "Import-Module PSReadLine -ErrorAction SilentlyContinue" in content
    assert "Invoke-Expression $decision.shell_code | Out-Host" in content
    assert "Write-MXTermStatus" in content
    assert "$rewritten = \"$env:MXTERM_HOOK_EXPLICIT_COMMAND '$escaped'\"" in content


def test_generate_hook_file_supports_natural_language_mode(tmp_path, monkeypatch):
    monkeypatch.setattr("mxterm.installer.bootstrap.hooks_dir", lambda: tmp_path)
    monkeypatch.setattr("mxterm.installer.profiles.hooks_dir", lambda: tmp_path)
    config = default_config()
    config.shell.auto_capture_mode = "natural_language"
    path = generate_hook_file("zsh", config=config)
    content = path.read_text(encoding="utf-8")
    assert 'export MXTERM_HOOK_AUTO_CAPTURE_MODE="natural_language"' in content
    assert '[[ "$mode" == "natural_language" ]] && return 1' in content
