from __future__ import annotations

from mxterm.models import RiskAssessment
from mxterm.safety.patterns import HIGH_RISK_PATTERNS, MEDIUM_RISK_PATTERNS


def assess_command(command: str, block_high_risk: bool = True) -> RiskAssessment:
    normalized = command.strip()
    if not normalized:
        return RiskAssessment(level="low", reasons=[])

    high_reasons = [reason for pattern, reason in HIGH_RISK_PATTERNS if pattern.search(normalized)]
    if high_reasons:
        return RiskAssessment(level="high", reasons=high_reasons, blocked=block_high_risk)

    medium_reasons = [reason for pattern, reason in MEDIUM_RISK_PATTERNS if pattern.search(normalized)]
    if medium_reasons:
        return RiskAssessment(level="medium", reasons=medium_reasons)

    return RiskAssessment(level="low", reasons=[])
