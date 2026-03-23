from __future__ import annotations

from mxterm.context.session import load_session


def recent_commands(limit: int = 10) -> list[str]:
    return load_session().recent_commands[-limit:]


def recent_failures(limit: int = 10) -> list[str]:
    return load_session().recent_failures[-limit:]
