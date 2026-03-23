from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class OllamaSettings:
    host: str
    model: str
    timeout_seconds: int = 60


@dataclass(slots=True)
class ShellSettings:
    preferred: str = "auto"
    confirm_mode: str = "auto_low_risk"
    auto_capture: bool = True
    auto_capture_mode: str = "smart"
    explicit_command: str = "mx"
    show_banner: bool = True


@dataclass(slots=True)
class SafetySettings:
    dry_run: bool = False
    block_high_risk: bool = True
    preview_ai_commands: bool = True
    permission_level: str = "medium"


@dataclass(slots=True)
class UISettings:
    theme: str = "mxterm"
    show_welcome: bool = True
    show_explanations: bool = True


@dataclass(slots=True)
class ContextSettings:
    history_limit: int = 20


@dataclass(slots=True)
class AgentSettings:
    enabled: bool = True
    max_steps: int = 5
    preflight_checks: bool = True
    confirm_each_step: bool = True
    retry_on_failure: bool = True
    max_retries: int = 1


@dataclass(slots=True)
class MXTermConfig:
    ollama: OllamaSettings
    shell: ShellSettings = field(default_factory=ShellSettings)
    safety: SafetySettings = field(default_factory=SafetySettings)
    ui: UISettings = field(default_factory=UISettings)
    context: ContextSettings = field(default_factory=ContextSettings)
    agent: AgentSettings = field(default_factory=AgentSettings)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SessionContext:
    cwd: str
    recent_commands: list[str] = field(default_factory=list)
    recent_failures: list[str] = field(default_factory=list)

    def trimmed(self, history_limit: int) -> "SessionContext":
        return SessionContext(
            cwd=self.cwd,
            recent_commands=self.recent_commands[-history_limit:],
            recent_failures=self.recent_failures[-history_limit:],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EnvironmentSummary:
    os_name: str
    shell: str
    path_style: str
    cwd: str
    available_tools: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TranslationStep:
    type: str
    command: str | None = None
    path: str | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AgentPreflightCheck:
    name: str
    ok: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AgentStepResult:
    step_index: int
    step_type: str
    command: str
    cwd: str
    attempts: int
    returncode: int
    ok: bool
    stdout: str = ""
    stderr: str = ""
    message: str = ""
    next_cwd: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AgentExecutionResult:
    ok: bool
    final_cwd: str
    preflight_checks: list[AgentPreflightCheck] = field(default_factory=list)
    step_results: list[AgentStepResult] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TranslationResult:
    intent: str
    language: str
    confidence: float
    explanation: str
    risk_hint: str
    requires_confirmation: bool
    steps: list[TranslationStep]
    task_mode: str = "single"
    plan_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "language": self.language,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "risk_hint": self.risk_hint,
            "requires_confirmation": self.requires_confirmation,
            "task_mode": self.task_mode,
            "plan_summary": self.plan_summary,
            "steps": [step.to_dict() for step in self.steps],
        }


@dataclass(slots=True)
class RiskAssessment:
    level: str
    reasons: list[str] = field(default_factory=list)
    blocked: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RouteDecision:
    route: str
    intent: str
    risk: str
    confidence: float
    requires_confirmation: bool
    display_command: str
    shell_code: str
    message: str
    original_input: str
    explanation: str = ""
    language: str = "unknown"
    risk_reasons: list[str] = field(default_factory=list)
    dry_run: bool = False
    source: str = "unknown"
    plan_summary: str = ""
    preview_items: list[str] = field(default_factory=list)
    preview_summary: str = ""
    steps: list[TranslationStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DoctorCheck:
    name: str
    ok: bool
    detail: str
