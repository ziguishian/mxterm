from mxterm.models import RouteDecision
from mxterm.ui.renderers import _hook_preview_lines, _status_line


def _decision(**overrides):
    data = {
        "route": "ai_translate",
        "intent": "List directories",
        "risk": "low",
        "confidence": 0.9,
        "requires_confirmation": False,
        "display_command": "Get-ChildItem -Directory",
        "shell_code": "Get-ChildItem -Directory",
        "message": "AI translation ready.",
        "original_input": "查看子目录",
        "explanation": "Use PowerShell to list directories.",
        "language": "zh",
        "risk_reasons": [],
        "dry_run": False,
        "source": "ai",
    }
    data.update(overrides)
    return RouteDecision(**data)


def test_status_line_uses_colored_ascii_dot():
    line = _status_line(_decision())
    assert "[bold green3]o[/bold green3]" in line
    assert "MXTerm Success" in line


def test_hook_preview_success_is_compact_multiline():
    lines = _hook_preview_lines(_decision(), model_name="qwen3:8b")
    assert len(lines) == 3
    assert any("qwen3:8b" in line for line in lines)
    assert any("Get-ChildItem -Directory" in line for line in lines)
    assert any("List directories" in line for line in lines)


def test_hook_preview_warning_includes_input_and_retry_hint():
    decision = _decision(
        route="block",
        display_command="",
        shell_code="",
        message="AI did not produce an executable command. Please enter another request.",
        explanation="The request did not map to a shell action.",
    )
    lines = _hook_preview_lines(decision, model_name="qwen3:8b")
    assert any("MXTerm Warning" in line for line in lines)
    assert any("Please enter another request." in line for line in lines)
    assert any("input" in line for line in lines)
