from __future__ import annotations

import glob
import os
import re
from pathlib import Path


POWERSHELL_REMOVE_PATTERN = re.compile(
    r"Remove-Item\s+-Path\s+(?P<quote>['\"])(?P<path>.+?)(?P=quote)",
    re.IGNORECASE,
)


def preview_destructive_targets(shell_name: str, shell_code: str, cwd: str, limit: int = 10) -> tuple[str, list[str]]:
    if shell_name == "powershell":
        return _preview_powershell_remove(shell_code, cwd=cwd, limit=limit)
    return ("", [])


def _preview_powershell_remove(shell_code: str, cwd: str, limit: int) -> tuple[str, list[str]]:
    match = POWERSHELL_REMOVE_PATTERN.search(shell_code)
    if not match:
        return ("", [])

    raw_path = match.group("path")
    expanded = raw_path
    if not os.path.isabs(expanded):
        expanded = str(Path(cwd, expanded).resolve())

    try:
        matches = sorted(glob.glob(expanded))
    except OSError:
        return ("", [])

    if "-file" in shell_code.lower():
        matches = [item for item in matches if Path(item).is_file()]
    elif "-directory" in shell_code.lower():
        matches = [item for item in matches if Path(item).is_dir()]

    if not matches:
        return ("No matching files were found for the destructive command preview.", [])

    shown = matches[:limit]
    summary = f"{len(matches)} target(s) will be affected. Showing up to {limit}."
    return (summary, shown)
