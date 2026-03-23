from pathlib import Path

from mxterm.context.session import load_session, reset_session


def test_reset_session_clears_history(tmp_path, monkeypatch):
    monkeypatch.setattr("mxterm.context.session.save_session", lambda session: None)
    session = reset_session(cwd=str(tmp_path))
    assert session.cwd == str(tmp_path)
    assert session.recent_commands == []
    assert session.recent_failures == []


def test_load_session_data_handles_empty_file(tmp_path, monkeypatch):
    session_file = tmp_path / "session.json"
    session_file.write_text("", encoding="utf-8")
    monkeypatch.setattr("mxterm.config.loader.session_path", lambda: session_file)
    from mxterm.config.loader import load_session_data

    assert load_session_data() == {}


def test_load_session_prefers_current_shell_cwd(monkeypatch):
    monkeypatch.setattr(
        "mxterm.context.session.load_session_data",
        lambda: {
            "cwd": "D:/stale/path",
            "recent_commands": ["mx 查看子目录"],
            "recent_failures": [],
        },
    )
    session = load_session("D:/actual/path")
    assert session.cwd == "D:/actual/path"
    assert session.recent_commands == ["mx 查看子目录"]
