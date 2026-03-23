from __future__ import annotations

import re

from mxterm.shell.capabilities import command_exists

NATURAL_LANGUAGE_HINTS = (
    "please",
    "show",
    "help",
    "open",
    "install",
    "start",
    "stop",
    "find",
    "list",
    "进入",
    "帮我",
    "请",
    "查看",
    "安装",
    "启动",
    "停止",
    "删除",
)
SHELL_OPERATORS = ("|", ">", "<", "&&", "||", ";")
COMPLEX_TASK_HINTS = (
    "然后",
    "再",
    "之后",
    "并且",
    "同时",
    "先",
    "接着",
    "最后",
    "then",
    "after",
    "and then",
    "next",
    "finally",
)


def contains_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def looks_like_natural_language(user_input: str) -> bool:
    lowered = user_input.lower()
    if contains_cjk(user_input):
        return True
    if any(hint in lowered for hint in NATURAL_LANGUAGE_HINTS):
        return True
    if lowered.endswith("?"):
        return True
    if " " in lowered and not lowered.startswith(("-", "./", ".\\")):
        tokens = lowered.split()
        if len(tokens) >= 3 and not any(token.startswith("-") for token in tokens[1:]):
            return True
    return False


def classify_input(user_input: str, shell_name: str) -> str:
    stripped = user_input.strip()
    if not stripped:
        return "empty"

    first_token = stripped.split()[0]
    if command_exists(first_token, shell_name):
        return "direct"
    if any(operator in stripped for operator in SHELL_OPERATORS):
        return "ambiguous"
    if looks_like_natural_language(stripped):
        return "natural_language"
    if re.match(r"^[a-zA-Z0-9_.-]+$", first_token):
        return "ambiguous"
    return "natural_language"


def looks_complex_task(user_input: str) -> bool:
    lowered = user_input.lower()
    if any(hint in user_input or hint in lowered for hint in COMPLEX_TASK_HINTS):
        return True
    if user_input.count("，") + user_input.count(",") >= 2:
        return True
    if user_input.count("并") >= 1 and len(user_input) > 12:
        return True
    return False
