from __future__ import annotations

from pathlib import Path

from mxterm.ai.ollama_client import OllamaClient, OllamaError
from mxterm.ai.translator import TranslationError, Translator, suggest_command
from mxterm.config.loader import load_config
from mxterm.constants import COMMON_TOOLS
from mxterm.context.session import load_session, record_command, record_failure, save_session
from mxterm.models import MXTermConfig, RouteDecision, SessionContext, TranslationResult
from mxterm.routing.classifier import classify_input
from mxterm.safety.preview import preview_destructive_targets
from mxterm.safety.assessor import assess_command
from mxterm.shell.adapters import render_steps
from mxterm.shell.capabilities import environment_summary


class MXTermPipeline:
    def __init__(self, config: MXTermConfig | None = None, translator: Translator | None = None) -> None:
        self.config = config or load_config()
        self.translator = translator or Translator(
            OllamaClient(
                host=self.config.ollama.host,
                timeout_seconds=self.config.ollama.timeout_seconds,
            )
        )

    def resolve(self, user_input: str, shell_name: str, cwd: str) -> RouteDecision:
        session = load_session(cwd).trimmed(self.config.context.history_limit)
        summary = environment_summary(cwd=cwd, shell_name=shell_name)
        classification = classify_input(user_input, shell_name)

        if classification == "empty":
            decision = RouteDecision(
                route="block",
                intent="Ignore empty input",
                risk="low",
                confidence=1.0,
                requires_confirmation=False,
                display_command="",
                shell_code="",
                message="Nothing to execute.",
                original_input=user_input,
                dry_run=self.config.safety.dry_run,
                source="empty",
            )
            return self._remember(decision, session)

        if classification == "direct":
            assessment = assess_command(user_input, block_high_risk=self.config.safety.block_high_risk)
            decision = RouteDecision(
                route="block" if assessment.blocked else "pass_through",
                intent="Execute direct shell command",
                risk=assessment.level,
                confidence=1.0,
                requires_confirmation=assessment.level != "low",
                display_command=user_input,
                shell_code="" if assessment.blocked else user_input,
                message="Direct command detected." if not assessment.blocked else "Blocked a high-risk direct command.",
                original_input=user_input,
                explanation="MXTerm detected that the input is already a valid shell command.",
                risk_reasons=assessment.reasons,
                dry_run=self.config.safety.dry_run,
                source="direct",
            )
            decision.requires_confirmation = self._apply_confirmation_policy(
                route=decision.route,
                risk=decision.risk,
                suggested=decision.requires_confirmation,
            )
            return self._remember(decision, session, next_cwd=self._direct_next_cwd(user_input, shell_name, session.cwd))

        if classification == "ambiguous":
            first_token = user_input.split()[0]
            suggestion = suggest_command(first_token, list(COMMON_TOOLS))
            if suggestion:
                suggested_command = user_input.replace(first_token, suggestion, 1)
                assessment = assess_command(suggested_command, block_high_risk=self.config.safety.block_high_risk)
                decision = RouteDecision(
                    route="suggest_fix",
                    intent="Suggest command correction",
                    risk=assessment.level,
                    confidence=0.55,
                    requires_confirmation=True,
                    display_command=suggested_command,
                    shell_code=suggested_command,
                    message=f"Did you mean: {suggested_command}",
                    original_input=user_input,
                    explanation="The input looks like a command but could not be resolved locally.",
                    risk_reasons=assessment.reasons,
                    dry_run=self.config.safety.dry_run,
                    source="suggestion",
                )
                decision.requires_confirmation = self._apply_confirmation_policy(
                    route=decision.route,
                    risk=decision.risk,
                    suggested=True,
                )
                return self._remember(decision, session)

        try:
            agent_mode = self.config.agent.enabled
            translation = self.translator.translate(
                user_input=user_input,
                summary=summary,
                session=session,
                model=self.config.ollama.model,
                agent_mode=agent_mode,
                max_steps=self.config.agent.max_steps,
            )
        except (OllamaError, TranslationError) as exc:
            decision = RouteDecision(
                route="block",
                intent="Translation unavailable",
                risk="medium",
                confidence=0.0,
                requires_confirmation=False,
                display_command="",
                shell_code="",
                message=f"Ollama translation failed: {exc}",
                original_input=user_input,
                explanation="MXTerm could not safely translate the natural language request.",
                dry_run=self.config.safety.dry_run,
                source="error",
            )
            return self._remember(decision, session, failure=decision.message)

        return self._from_translation(user_input, shell_name, translation, session, agent_mode=agent_mode)

    def _from_translation(
        self,
        user_input: str,
        shell_name: str,
        translation: TranslationResult,
        session: SessionContext,
        agent_mode: bool,
    ) -> RouteDecision:
        executable_steps = [step for step in translation.steps if self._is_executable_step(step)]
        shell_code = render_steps(shell_name, executable_steps)
        preview_summary, preview_items = preview_destructive_targets(shell_name, shell_code, session.cwd)
        source = "agent" if agent_mode or translation.task_mode == "agent" or len(executable_steps) > 1 else "ai"
        if not shell_code.strip():
            decision = RouteDecision(
                route="block",
                intent=translation.intent,
                risk=translation.risk_hint,
                confidence=translation.confidence,
                requires_confirmation=False,
                display_command="",
                shell_code="",
                message="AI did not produce an executable command. Please enter another request.",
                original_input=user_input,
                explanation=translation.explanation or "The request did not map to a shell action.",
                language=translation.language,
                dry_run=self.config.safety.dry_run,
                source=source,
                plan_summary=translation.plan_summary,
                steps=executable_steps,
            )
            return self._remember(decision, session, failure=decision.message)
        assessment = assess_command(shell_code, block_high_risk=self.config.safety.block_high_risk)
        route = "block" if assessment.blocked else "ai_translate"
        next_cwd = self._translated_next_cwd(executable_steps, session.cwd)
        decision = RouteDecision(
            route=route,
            intent=translation.intent,
            risk=assessment.level if shell_code else translation.risk_hint,
            confidence=translation.confidence,
            requires_confirmation=translation.requires_confirmation or assessment.level != "low" or bool(preview_items) or source == "agent",
            display_command=shell_code,
            shell_code="" if route == "block" else shell_code,
            message=("Agent plan ready." if source == "agent" else "AI translation ready.") if route != "block" else "Blocked a high-risk AI-generated command.",
            original_input=user_input,
            explanation=translation.explanation,
            language=translation.language,
            risk_reasons=assessment.reasons,
            dry_run=self.config.safety.dry_run,
            source=source,
            plan_summary=translation.plan_summary,
            preview_items=preview_items,
            preview_summary=preview_summary,
            steps=executable_steps,
        )
        decision.requires_confirmation = self._apply_confirmation_policy(
            route=decision.route,
            risk=decision.risk,
            suggested=decision.requires_confirmation,
        )
        return self._remember(decision, session, next_cwd=next_cwd)

    def _is_executable_step(self, step: object) -> bool:
        step_type = getattr(step, "type", None)
        if step_type == "shell":
            return bool(getattr(step, "command", None))
        if step_type == "chdir":
            return bool(getattr(step, "path", None))
        return False

    def _remember(
        self,
        decision: RouteDecision,
        session: SessionContext,
        next_cwd: str | None = None,
        failure: str | None = None,
    ) -> RouteDecision:
        if next_cwd:
            session.cwd = next_cwd
        if failure or decision.route == "block":
            message = failure or decision.message
            record_failure(session, message, self.config.context.history_limit)
        updated = record_command(session, decision.original_input, self.config.context.history_limit)
        save_session(updated)
        return decision

    def _translated_next_cwd(self, steps: list, current_cwd: str) -> str | None:
        for step in reversed(steps):
            if getattr(step, "type", None) == "chdir" and getattr(step, "path", None):
                return str(Path(current_cwd, step.path).resolve()) if not Path(step.path).is_absolute() else str(Path(step.path))
        return None

    def _direct_next_cwd(self, command: str, shell_name: str, current_cwd: str) -> str | None:
        stripped = command.strip()
        if not stripped:
            return None
        tokens = stripped.split(maxsplit=1)
        head = tokens[0].lower()
        tail = tokens[1].strip() if len(tokens) > 1 else ""
        if shell_name in {"bash", "zsh"} and head == "cd" and tail:
            return str(Path(current_cwd, tail).resolve()) if not Path(tail).is_absolute() else str(Path(tail))
        if shell_name == "powershell" and head in {"cd", "chdir", "set-location"} and tail:
            cleaned = tail.replace("-LiteralPath", "").replace("-Path", "").strip().strip("'\"")
            return str(Path(current_cwd, cleaned).resolve()) if not Path(cleaned).is_absolute() else str(Path(cleaned))
        return None

    def _apply_confirmation_policy(self, route: str, risk: str, suggested: bool) -> bool:
        mode = self.config.shell.confirm_mode.lower()
        permission = self.config.safety.permission_level.lower()
        if self.config.safety.dry_run:
            return False
        if permission == "high":
            return False
        if permission == "low":
            return route != "block"
        if mode == "always":
            return route in {"ai_translate", "suggest_fix", "pass_through"} and route != "block"
        if mode == "never":
            return False
        return suggested
