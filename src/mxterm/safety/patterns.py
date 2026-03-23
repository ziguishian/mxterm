from __future__ import annotations

import re

HIGH_RISK_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\brm\s+-rf\b", re.IGNORECASE), "Detected recursive force delete."),
    (re.compile(r"\bmkfs\b", re.IGNORECASE), "Detected filesystem formatting command."),
    (re.compile(r"\bdd\b", re.IGNORECASE), "Detected raw disk copy command."),
    (re.compile(r"\bshutdown\b", re.IGNORECASE), "Detected system shutdown command."),
    (re.compile(r"\breboot\b", re.IGNORECASE), "Detected reboot command."),
    (re.compile(r"\bformat\b", re.IGNORECASE), "Detected disk formatting command."),
    (re.compile(r"\bdel\s+/s\b", re.IGNORECASE), "Detected recursive delete on Windows."),
    (re.compile(r">\s*/(etc|usr|bin|sbin)/", re.IGNORECASE), "Detected overwrite to a system path."),
    (re.compile(r">\s*C:\\Windows\\", re.IGNORECASE), "Detected overwrite to a Windows system path."),
]

MEDIUM_RISK_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bsudo\b", re.IGNORECASE), "Uses elevated privileges."),
    (re.compile(r"&&|\|\|", re.IGNORECASE), "Contains chained commands."),
    (re.compile(r"[|]", re.IGNORECASE), "Contains a pipe."),
    (re.compile(r">\s*", re.IGNORECASE), "Contains output redirection."),
    (re.compile(r"\b(chmod|chown)\b", re.IGNORECASE), "Changes permissions or ownership."),
]
