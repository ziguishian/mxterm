from __future__ import annotations

import json

from mxterm.models import EnvironmentSummary, SessionContext

OUTPUT_SCHEMA = {
    "intent": "short description of user intent",
    "language": "zh|en|other",
    "confidence": 0.0,
    "explanation": "brief explanation",
    "risk_hint": "low|medium|high",
    "requires_confirmation": False,
    "task_mode": "single|agent",
    "plan_summary": "short plan summary for the intended shell actions",
    "steps": [
        {"type": "shell|chdir|message", "command": "optional command", "path": "optional path", "message": "optional message"}
    ],
}


def build_system_prompt(summary: EnvironmentSummary, session: SessionContext) -> str:
    return (
        "You are MXTerm, a shell command translator. "
        "Translate natural language into safe shell actions for the current environment. "
        "Never chat. Never explain more than necessary. "
        "If the input is only a greeting, casual chat, or not an executable shell request, return an empty steps array. "
        "If the request is unsafe or ambiguous, return conservative output and set requires_confirmation to true. "
        "Output strict JSON only, no markdown fences.\n\n"
        f"Environment: {json.dumps(summary.to_dict(), ensure_ascii=False)}\n"
        f"Session: {json.dumps(session.to_dict(), ensure_ascii=False)}\n"
        f"Schema: {json.dumps(OUTPUT_SCHEMA, ensure_ascii=False)}"
    )


def build_user_prompt(user_input: str, agent_mode: bool = False, max_steps: int = 5) -> str:
    if agent_mode:
        return (
            "Translate the following input in agent mode. "
            f"You may decompose the task into up to {max_steps} ordered shell steps when needed. "
            "For simple requests, return a single safe shell step. "
            "For multi-step requests, prefer inspection before mutation and keep each step explicit and conservative. "
            "Set task_mode to agent and provide a short plan_summary even when the result is a single executable step.\n\n"
            f"User input: {user_input}"
        )
    return (
        "Translate the following input into shell steps. "
        "Prefer a single command when possible. "
        "Use the current shell syntax and keep paths consistent with the current OS.\n\n"
        f"User input: {user_input}"
    )
