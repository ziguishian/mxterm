from __future__ import annotations

from pathlib import Path

from mxterm.config.loader import load_session_data, save_session_data
from mxterm.models import SessionContext


def load_session(cwd: str | None = None) -> SessionContext:
    raw = load_session_data()
    default_cwd = cwd or str(Path.cwd())
    return SessionContext(
        cwd=default_cwd,
        recent_commands=list(raw.get("recent_commands", [])),
        recent_failures=list(raw.get("recent_failures", [])),
    )


def save_session(session: SessionContext) -> None:
    save_session_data(
        {
            "cwd": session.cwd,
            "recent_commands": session.recent_commands,
            "recent_failures": session.recent_failures,
        }
    )


def record_command(session: SessionContext, command: str, history_limit: int) -> SessionContext:
    session.recent_commands.append(command)
    session.recent_commands = session.recent_commands[-history_limit:]
    return session


def record_failure(session: SessionContext, failure: str, history_limit: int) -> SessionContext:
    session.recent_failures.append(failure)
    session.recent_failures = session.recent_failures[-history_limit:]
    return session


def reset_session(cwd: str | None = None) -> SessionContext:
    session = SessionContext(cwd=cwd or str(Path.cwd()))
    save_session(session)
    return session
