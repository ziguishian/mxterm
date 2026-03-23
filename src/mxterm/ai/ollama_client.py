from __future__ import annotations

import httpx


class OllamaError(RuntimeError):
    """Raised when Ollama cannot satisfy a request."""


class OllamaClient:
    def __init__(self, host: str, timeout_seconds: int = 60) -> None:
        self.host = host.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def ping(self) -> tuple[bool, str]:
        try:
            response = httpx.get(f"{self.host}/api/tags", timeout=self.timeout_seconds)
            response.raise_for_status()
        except Exception as exc:  # pragma: no cover
            return False, str(exc)
        return True, "Ollama API reachable"

    def list_models(self) -> list[str]:
        response = httpx.get(f"{self.host}/api/tags", timeout=self.timeout_seconds)
        response.raise_for_status()
        data = response.json()
        return [item.get("name", "") for item in data.get("models", []) if item.get("name")]

    def generate(self, model: str, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {"temperature": 0.1},
        }
        try:
            response = httpx.post(f"{self.host}/api/generate", json=payload, timeout=self.timeout_seconds)
            response.raise_for_status()
        except Exception as exc:  # pragma: no cover
            raise OllamaError(str(exc)) from exc
        data = response.json()
        text = data.get("response")
        if not isinstance(text, str) or not text.strip():
            raise OllamaError("Ollama returned an empty response.")
        return text
