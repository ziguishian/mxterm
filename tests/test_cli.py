from typer.testing import CliRunner

from mxterm.cli import app
from mxterm.config.defaults import default_config


runner = CliRunner()


def test_help_command_renders_overview(monkeypatch):
    captured = {}
    config = default_config()

    monkeypatch.setattr("mxterm.cli.ensure_runtime_dirs", lambda: None)
    monkeypatch.setattr("mxterm.cli.load_config", lambda: config)

    def fake_render_help_overview(value):
        captured["model"] = value.ollama.model

    monkeypatch.setattr("mxterm.cli.render_help_overview", fake_render_help_overview)
    result = runner.invoke(app, ["help"])
    assert result.exit_code == 0
    assert captured["model"] == config.ollama.model


def test_model_current_prints_configured_model(monkeypatch):
    config = default_config()
    config.ollama.model = "qwen3:14b"
    monkeypatch.setattr("mxterm.cli.load_config", lambda: config)
    result = runner.invoke(app, ["model", "current"])
    assert result.exit_code == 0
    assert "qwen3:14b" in result.stdout


def test_model_use_updates_config(monkeypatch):
    config = default_config()
    saved = {}

    class FakeClient:
        def __init__(self, host, timeout_seconds=60):
            self.host = host
            self.timeout_seconds = timeout_seconds

        def list_models(self):
            return ["qwen3:8b", "qwen3:14b"]

    monkeypatch.setattr("mxterm.cli.ensure_runtime_dirs", lambda: None)
    monkeypatch.setattr("mxterm.cli.load_config", lambda: config)
    monkeypatch.setattr("mxterm.cli.OllamaClient", FakeClient)

    def fake_save_config(value):
        saved["model"] = value.ollama.model
        return "mock-config.toml"

    monkeypatch.setattr("mxterm.cli.save_config", fake_save_config)
    result = runner.invoke(app, ["model", "use", "qwen3:14b"])
    assert result.exit_code == 0
    assert saved["model"] == "qwen3:14b"
    assert "qwen3:14b" in result.stdout


def test_model_use_rejects_unknown_model(monkeypatch):
    config = default_config()

    class FakeClient:
        def __init__(self, host, timeout_seconds=60):
            self.host = host
            self.timeout_seconds = timeout_seconds

        def list_models(self):
            return ["qwen3:8b"]

    monkeypatch.setattr("mxterm.cli.ensure_runtime_dirs", lambda: None)
    monkeypatch.setattr("mxterm.cli.load_config", lambda: config)
    monkeypatch.setattr("mxterm.cli.OllamaClient", FakeClient)
    result = runner.invoke(app, ["model", "use", "qwen3:14b"])
    assert result.exit_code == 1
    assert "not installed" in result.stdout


def test_permission_current_prints_configured_level(monkeypatch):
    config = default_config()
    config.safety.permission_level = "high"
    monkeypatch.setattr("mxterm.cli.load_config", lambda: config)
    result = runner.invoke(app, ["permission", "current"])
    assert result.exit_code == 0
    assert "high" in result.stdout


def test_permission_use_updates_config(monkeypatch):
    config = default_config()
    saved = {}
    monkeypatch.setattr("mxterm.cli.ensure_runtime_dirs", lambda: None)
    monkeypatch.setattr("mxterm.cli.load_config", lambda: config)

    def fake_save_config(value):
        saved["permission_level"] = value.safety.permission_level
        return "mock-config.toml"

    monkeypatch.setattr("mxterm.cli.save_config", fake_save_config)
    result = runner.invoke(app, ["permission", "use", "low"])
    assert result.exit_code == 0
    assert saved["permission_level"] == "low"
    assert "low" in result.stdout
