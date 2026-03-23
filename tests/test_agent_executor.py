from pathlib import Path
from types import SimpleNamespace

from mxterm.agent.executor import build_preflight_checks, execute_agent_plan
from mxterm.models import TranslationStep


def test_preflight_detects_missing_directory(tmp_path):
    steps = [TranslationStep(type="chdir", path="missing-dir")]
    checks = build_preflight_checks("powershell", steps, str(tmp_path))
    assert len(checks) == 1
    assert checks[0].ok is False


def test_execute_agent_plan_retries_failed_step(monkeypatch, tmp_path):
    attempts = {"count": 0}

    def fake_run_shell_code(shell_name, shell_code, cwd):
        attempts["count"] += 1
        if attempts["count"] == 1:
            return SimpleNamespace(returncode=1, stdout="", stderr="first failure")
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("mxterm.agent.executor.run_shell_code", fake_run_shell_code)
    result = execute_agent_plan(
        "powershell",
        [TranslationStep(type="shell", command="Write-Output 'hello'")],
        str(tmp_path),
        preflight_checks=False,
        retry_on_failure=True,
        max_retries=1,
    )
    assert result.ok is True
    assert result.step_results[0].attempts == 2
    assert attempts["count"] == 2


def test_execute_agent_plan_updates_cwd_for_chdir(tmp_path):
    target = tmp_path / "child"
    target.mkdir()
    result = execute_agent_plan(
        "bash",
        [TranslationStep(type="chdir", path="child")],
        str(tmp_path),
        preflight_checks=True,
        retry_on_failure=False,
        max_retries=0,
    )
    assert result.ok is True
    assert Path(result.final_cwd) == target


def test_execute_agent_plan_can_cancel_before_step(tmp_path):
    result = execute_agent_plan(
        "bash",
        [TranslationStep(type="shell", command="printf 'hello\\n'")],
        str(tmp_path),
        preflight_checks=False,
        retry_on_failure=False,
        max_retries=0,
        confirm_callback=lambda index, step, cwd, rendered: False,
    )
    assert result.ok is False
    assert "cancelled" in result.message.lower()
