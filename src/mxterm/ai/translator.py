from __future__ import annotations

import json
from difflib import get_close_matches

from mxterm.ai.ollama_client import OllamaClient
from mxterm.ai.prompt_builder import build_system_prompt, build_user_prompt
from mxterm.models import EnvironmentSummary, SessionContext, TranslationResult, TranslationStep


class TranslationError(RuntimeError):
    """Raised when translation fails."""


def _extract_json_object(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise TranslationError("Model response did not contain JSON.")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise TranslationError(f"Invalid JSON from model: {exc}") from exc


def _coerce_steps(raw_steps: list[dict]) -> list[TranslationStep]:
    steps: list[TranslationStep] = []
    for item in raw_steps:
        steps.append(
            TranslationStep(
                type=str(item.get("type", "shell")),
                command=item.get("command"),
                path=item.get("path"),
                message=item.get("message"),
            )
        )
    return steps


class Translator:
    def __init__(self, client: OllamaClient) -> None:
        self.client = client

    def translate(
        self,
        user_input: str,
        summary: EnvironmentSummary,
        session: SessionContext,
        model: str,
        agent_mode: bool = False,
        max_steps: int = 5,
    ) -> TranslationResult:
        raw = self.client.generate(
            model=model,
            system_prompt=build_system_prompt(summary, session),
            user_prompt=build_user_prompt(user_input, agent_mode=agent_mode, max_steps=max_steps),
        )
        data = _extract_json_object(raw)
        return TranslationResult(
            intent=str(data.get("intent", "Translate natural language to shell command")),
            language=str(data.get("language", "other")),
            confidence=float(data.get("confidence", 0.0)),
            explanation=str(data.get("explanation", "")),
            risk_hint=str(data.get("risk_hint", "medium")),
            requires_confirmation=bool(data.get("requires_confirmation", False)),
            steps=_coerce_steps(list(data.get("steps", []))),
            task_mode=str(data.get("task_mode", "agent" if agent_mode else "single")),
            plan_summary=str(data.get("plan_summary", "")),
        )


def suggest_command(token: str, candidates: list[str]) -> str | None:
    matches = get_close_matches(token, candidates, n=1, cutoff=0.75)
    return matches[0] if matches else None
