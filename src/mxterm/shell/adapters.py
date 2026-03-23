from __future__ import annotations

import shlex

from mxterm.models import TranslationStep


def quote_for_shell(shell_name: str, value: str) -> str:
    if shell_name == "powershell":
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    return shlex.quote(value)


def join_input_tokens(tokens: list[str]) -> str:
    return " ".join(tokens).strip()


def render_steps(shell_name: str, steps: list[TranslationStep]) -> str:
    rendered: list[str] = []
    for step in steps:
        if step.type == "shell" and step.command:
            rendered.append(step.command)
        elif step.type == "chdir" and step.path:
            if shell_name == "powershell":
                rendered.append(f"Set-Location -LiteralPath {quote_for_shell(shell_name, step.path)}")
            else:
                rendered.append(f"cd {quote_for_shell(shell_name, step.path)}")
        elif step.type == "message" and step.message:
            if shell_name == "powershell":
                rendered.append(f"Write-Host {quote_for_shell(shell_name, step.message)}")
            else:
                rendered.append(f"printf '%s\\n' {quote_for_shell(shell_name, step.message)}")
    separator = "; " if shell_name == "powershell" else " && "
    return separator.join(rendered)
