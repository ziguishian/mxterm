from __future__ import annotations

APP_NAME = "MXTerm"
APP_SLUG = "mxterm"
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "qwen3:8b"
PROFILE_MARKER_START = "# >>> MXTerm initialize >>>"
PROFILE_MARKER_END = "# <<< MXTerm initialize <<<"
WINDOWS_PROFILE_MARKER_START = "# >>> MXTerm initialize >>>"
WINDOWS_PROFILE_MARKER_END = "# <<< MXTerm initialize <<<"
SUPPORTED_SHELLS = ("zsh", "bash", "powershell")
COMMON_TOOLS = (
    "git",
    "python",
    "node",
    "npm",
    "pnpm",
    "pip",
    "pipx",
    "ollama",
    "brew",
    "apt",
    "apt-get",
    "yum",
    "dnf",
    "pacman",
    "cargo",
)
DEFAULT_CONFIG_TEXT = """[ollama]
host = "http://127.0.0.1:11434"
model = "qwen3:8b"
timeout_seconds = 60

[shell]
preferred = "auto"
confirm_mode = "auto_low_risk"
auto_capture = true
auto_capture_mode = "smart"
explicit_command = "mx"
show_banner = true

[safety]
dry_run = false
block_high_risk = true
preview_ai_commands = true
permission_level = "medium"

[ui]
theme = "mxterm"
show_welcome = true
show_explanations = true

[context]
history_limit = 20

[agent]
enabled = true
max_steps = 5
preflight_checks = true
confirm_each_step = true
retry_on_failure = true
max_retries = 1
"""
