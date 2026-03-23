from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mxterm.config.loader import ensure_runtime_dirs, logs_dir


def _normalize(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    return value


def log_event(event_type: str, payload: dict[str, Any]) -> Path:
    ensure_runtime_dirs()
    path = log_path()
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "payload": {key: _normalize(value) for key, value in payload.items()},
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def log_path() -> Path:
    ensure_runtime_dirs()
    return logs_dir() / "mxterm.log.jsonl"


def tail_logs(lines: int = 20) -> list[str]:
    path = log_path()
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()[-lines:]


def clear_logs() -> Path:
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    return path
