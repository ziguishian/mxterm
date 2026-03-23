from mxterm.ai.prompt_builder import build_system_prompt
from mxterm.models import EnvironmentSummary, SessionContext


def test_prompt_contains_environment_and_session_data():
    prompt = build_system_prompt(
        EnvironmentSummary(
            os_name="linux",
            shell="bash",
            path_style="posix",
            cwd="/tmp/project",
            available_tools=["git", "python"],
        ),
        SessionContext(cwd="/tmp/project", recent_commands=["git status"], recent_failures=["missing file"]),
    )
    assert "linux" in prompt
    assert "git status" in prompt
    assert "missing file" in prompt
    assert "empty steps array" in prompt
