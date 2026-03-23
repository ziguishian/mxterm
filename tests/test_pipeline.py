from mxterm.config.defaults import default_config
from mxterm.models import SessionContext, TranslationResult, TranslationStep
from mxterm.routing.pipeline import MXTermPipeline


class FakeTranslator:
    def __init__(self):
        self.calls = []

    def translate(self, user_input, summary, session, model, agent_mode=False, max_steps=5):
        self.calls.append(
            {
                "user_input": user_input,
                "agent_mode": agent_mode,
                "max_steps": max_steps,
            }
        )
        return TranslationResult(
            intent="List files",
            language="en",
            confidence=0.9,
            explanation="Use ls to list files.",
            risk_hint="low",
            requires_confirmation=False,
            task_mode="agent" if agent_mode else "single",
            plan_summary="Inspect the current folder and list its contents." if agent_mode else "",
            steps=[TranslationStep(type="shell", command="ls -la")],
        )


class FakeTranslatorChdir:
    def translate(self, user_input, summary, session, model, agent_mode=False, max_steps=5):
        return TranslationResult(
            intent="Change directory",
            language="zh",
            confidence=0.95,
            explanation="Change the current working directory.",
            risk_hint="low",
            requires_confirmation=False,
            task_mode="agent" if agent_mode else "single",
            plan_summary="Move to the parent directory." if agent_mode else "",
            steps=[TranslationStep(type="chdir", path="..")],
        )


class FakeTranslatorMessageOnly:
    def translate(self, user_input, summary, session, model, agent_mode=False, max_steps=5):
        return TranslationResult(
            intent="Greeting",
            language="zh",
            confidence=0.8,
            explanation="Greeting only, no shell action needed.",
            risk_hint="low",
            requires_confirmation=False,
            task_mode="agent" if agent_mode else "single",
            plan_summary="No executable shell action is needed." if agent_mode else "",
            steps=[TranslationStep(type="message", message="hello")],
        )


class FakeTranslatorAgent:
    def translate(self, user_input, summary, session, model, agent_mode=False, max_steps=5):
        return TranslationResult(
            intent="Bootstrap project",
            language="en",
            confidence=0.92,
            explanation="Inspect files first, then install dependencies, then start the app.",
            risk_hint="medium",
            requires_confirmation=False,
            task_mode="agent",
            plan_summary="Inspect the repo, install dependencies, then start the service.",
            steps=[
                TranslationStep(type="shell", command="Get-ChildItem"),
                TranslationStep(type="shell", command="npm install"),
                TranslationStep(type="shell", command="npm run dev"),
            ],
        )


def test_pipeline_direct_pass_through(monkeypatch):
    monkeypatch.setattr("mxterm.routing.pipeline.load_session", lambda cwd: SessionContext(cwd=cwd))
    monkeypatch.setattr("mxterm.routing.pipeline.save_session", lambda session: None)
    monkeypatch.setattr("mxterm.routing.pipeline.classify_input", lambda user_input, shell_name: "direct")
    pipeline = MXTermPipeline(config=default_config(), translator=FakeTranslator())
    decision = pipeline.resolve("git status", "bash", "/tmp")
    assert decision.route == "pass_through"
    assert decision.display_command == "git status"


def test_pipeline_low_permission_confirms_direct_commands(monkeypatch):
    config = default_config()
    config.safety.permission_level = "low"
    monkeypatch.setattr("mxterm.routing.pipeline.load_session", lambda cwd: SessionContext(cwd=cwd))
    monkeypatch.setattr("mxterm.routing.pipeline.save_session", lambda session: None)
    monkeypatch.setattr("mxterm.routing.pipeline.classify_input", lambda user_input, shell_name: "direct")
    pipeline = MXTermPipeline(config=config, translator=FakeTranslator())
    decision = pipeline.resolve("git status", "bash", "/tmp")
    assert decision.requires_confirmation is True


def test_pipeline_high_permission_skips_confirmation(monkeypatch):
    config = default_config()
    config.safety.permission_level = "high"
    monkeypatch.setattr("mxterm.routing.pipeline.load_session", lambda cwd: SessionContext(cwd=cwd))
    monkeypatch.setattr("mxterm.routing.pipeline.save_session", lambda session: None)
    monkeypatch.setattr("mxterm.routing.pipeline.classify_input", lambda user_input, shell_name: "natural_language")
    translator = FakeTranslator()
    pipeline = MXTermPipeline(config=config, translator=translator)
    decision = pipeline.resolve("list files", "bash", "/tmp")
    assert decision.requires_confirmation is False


def test_pipeline_natural_language_uses_agent_by_default(monkeypatch):
    monkeypatch.setattr("mxterm.routing.pipeline.load_session", lambda cwd: SessionContext(cwd=cwd))
    monkeypatch.setattr("mxterm.routing.pipeline.save_session", lambda session: None)
    monkeypatch.setattr("mxterm.routing.pipeline.classify_input", lambda user_input, shell_name: "natural_language")
    translator = FakeTranslator()
    pipeline = MXTermPipeline(config=default_config(), translator=translator)
    decision = pipeline.resolve("list files", "bash", "/tmp")
    assert decision.route == "ai_translate"
    assert decision.display_command == "ls -la"
    assert decision.source == "agent"
    assert decision.plan_summary.startswith("Inspect the current folder")
    assert decision.requires_confirmation is True
    assert translator.calls[-1]["agent_mode"] is True


def test_pipeline_updates_session_cwd_for_chdir(monkeypatch):
    captured = {}

    monkeypatch.setattr("mxterm.routing.pipeline.load_session", lambda cwd: SessionContext(cwd=cwd))

    def fake_save_session(session):
        captured["cwd"] = session.cwd

    monkeypatch.setattr("mxterm.routing.pipeline.save_session", fake_save_session)
    monkeypatch.setattr("mxterm.routing.pipeline.classify_input", lambda user_input, shell_name: "natural_language")
    pipeline = MXTermPipeline(config=default_config(), translator=FakeTranslatorChdir())
    decision = pipeline.resolve("go to the parent directory", "bash", "/tmp/project")
    assert decision.route == "ai_translate"
    assert decision.display_command == "cd .."
    assert captured["cwd"].endswith("\\tmp") or captured["cwd"].endswith("/tmp")


def test_pipeline_respects_dry_run(monkeypatch):
    config = default_config()
    config.safety.dry_run = True
    monkeypatch.setattr("mxterm.routing.pipeline.load_session", lambda cwd: SessionContext(cwd=cwd))
    monkeypatch.setattr("mxterm.routing.pipeline.save_session", lambda session: None)
    monkeypatch.setattr("mxterm.routing.pipeline.classify_input", lambda user_input, shell_name: "natural_language")
    pipeline = MXTermPipeline(config=config, translator=FakeTranslator())
    decision = pipeline.resolve("list files", "bash", "/tmp")
    assert decision.dry_run is True
    assert decision.requires_confirmation is False


def test_pipeline_confirm_mode_always(monkeypatch):
    config = default_config()
    config.shell.confirm_mode = "always"
    monkeypatch.setattr("mxterm.routing.pipeline.load_session", lambda cwd: SessionContext(cwd=cwd))
    monkeypatch.setattr("mxterm.routing.pipeline.save_session", lambda session: None)
    monkeypatch.setattr("mxterm.routing.pipeline.classify_input", lambda user_input, shell_name: "natural_language")
    pipeline = MXTermPipeline(config=config, translator=FakeTranslator())
    decision = pipeline.resolve("list files", "bash", "/tmp")
    assert decision.requires_confirmation is True


def test_pipeline_can_disable_agent_mode(monkeypatch):
    config = default_config()
    config.agent.enabled = False
    monkeypatch.setattr("mxterm.routing.pipeline.load_session", lambda cwd: SessionContext(cwd=cwd))
    monkeypatch.setattr("mxterm.routing.pipeline.save_session", lambda session: None)
    monkeypatch.setattr("mxterm.routing.pipeline.classify_input", lambda user_input, shell_name: "natural_language")
    translator = FakeTranslator()
    pipeline = MXTermPipeline(config=config, translator=translator)
    decision = pipeline.resolve("list files", "bash", "/tmp")
    assert decision.route == "ai_translate"
    assert decision.source == "ai"
    assert decision.requires_confirmation is False
    assert translator.calls[-1]["agent_mode"] is False


def test_pipeline_blocks_message_only_translation(monkeypatch):
    monkeypatch.setattr("mxterm.routing.pipeline.load_session", lambda cwd: SessionContext(cwd=cwd))
    monkeypatch.setattr("mxterm.routing.pipeline.save_session", lambda session: None)
    monkeypatch.setattr("mxterm.routing.pipeline.classify_input", lambda user_input, shell_name: "natural_language")
    pipeline = MXTermPipeline(config=default_config(), translator=FakeTranslatorMessageOnly())
    decision = pipeline.resolve("hello", "powershell", "/tmp")
    assert decision.route == "block"
    assert decision.shell_code == ""
    assert decision.source == "agent"
    assert "Please enter another request" in decision.message


def test_pipeline_preserves_multi_step_agent_plan(monkeypatch):
    monkeypatch.setattr("mxterm.routing.pipeline.load_session", lambda cwd: SessionContext(cwd=cwd))
    monkeypatch.setattr("mxterm.routing.pipeline.save_session", lambda session: None)
    monkeypatch.setattr("mxterm.routing.pipeline.classify_input", lambda user_input, shell_name: "natural_language")
    pipeline = MXTermPipeline(config=default_config(), translator=FakeTranslatorAgent())
    decision = pipeline.resolve("inspect the repo, install dependencies, then start it", "powershell", "/tmp")
    assert decision.source == "agent"
    assert decision.plan_summary.startswith("Inspect the repo")
    assert decision.requires_confirmation is True
