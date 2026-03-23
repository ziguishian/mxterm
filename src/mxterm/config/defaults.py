from __future__ import annotations

from mxterm.constants import DEFAULT_CONFIG_TEXT, DEFAULT_OLLAMA_HOST, DEFAULT_OLLAMA_MODEL
from mxterm.models import AgentSettings, ContextSettings, MXTermConfig, OllamaSettings, SafetySettings, ShellSettings, UISettings


def default_config() -> MXTermConfig:
    return MXTermConfig(
        ollama=OllamaSettings(host=DEFAULT_OLLAMA_HOST, model=DEFAULT_OLLAMA_MODEL),
        shell=ShellSettings(),
        safety=SafetySettings(),
        ui=UISettings(),
        context=ContextSettings(),
        agent=AgentSettings(),
    )


def default_config_text() -> str:
    return DEFAULT_CONFIG_TEXT
