# MXTerm

MXTerm is a cross-platform shell enhancement tool that adds natural-language command translation, safety checks, session-aware shell actions, agent-style planning, and Ollama-powered intent resolution to existing shells.

[简体中文](README.md)

## Supported Platforms

- macOS: `zsh` primary, `bash` secondary
- Linux: `bash` primary, `zsh` secondary
- Windows: PowerShell 7+ primary, Windows PowerShell 5.1 basic support

Any terminal application that launches one of these shells can use MXTerm after installation, including Terminal.app, iTerm2, GNOME Terminal, Windows Terminal, and VS Code Terminal.

## Install

### Recommended: install directly from GitHub

```bash
pipx install git+https://github.com/ziguishian/mxterm.git
mxterm config init
mxterm install --shell auto
```

### If you already cloned the repository

You can also install a local editable development build:

```bash
python -m pip install -e .[dev]
mxterm config init
mxterm install --shell auto
```

### One-line installers

```bash
curl -fsSL https://raw.githubusercontent.com/ziguishian/mxterm/main/scripts/install/install.sh | sh
```

```powershell
irm https://raw.githubusercontent.com/ziguishian/mxterm/main/scripts/install/install.ps1 | iex
```

### Switch to PyPI later

This README currently defaults to GitHub installation. After MXTerm is published on PyPI, you can switch the primary install command to:

```bash
pipx install mxterm
```

### Binary releases

GitHub Releases can ship:

- `mxterm-macos-universal.tar.gz`
- `mxterm-linux-x86_64.tar.gz`
- `mxterm-windows-x64.zip`

## Quick Start

1. Install MXTerm.
2. Run `mxterm install --shell auto`.
3. Restart the shell, or reload the profile.
4. Type natural language directly, or use `mx` explicitly.

Examples:

```bash
help me list files in this folder
mx install dependencies for this project
gti status
```

## CLI Commands

```bash
mxterm doctor
mxterm doctor --json
mxterm help
mxterm config init
mxterm config path
mxterm config show --json
mxterm install --shell auto
mxterm uninstall --shell auto
mxterm hooks path --shell bash
mxterm hooks refresh --shell bash
mxterm hooks show --shell zsh
mxterm hooks doctor --shell zsh
mxterm model list
mxterm model current
mxterm model use qwen3:14b
mxterm permission current
mxterm permission use high
mxterm resolve --shell bash --cwd "$PWD" --input "show files here"
mxterm explain --shell powershell --cwd . --input "find large files here"
mxterm run --shell powershell --cwd . --input "show files here" --yes
mxterm history
mxterm session
mxterm reset-session
mxterm runtime
mxterm logs path
mxterm logs tail -n 20
mxterm logs clear
mxterm self-update
```

## How It Works

- Valid shell commands pass through directly.
- Unknown or natural-language input is routed into MXTerm.
- MXTerm detects platform, shell, path style, and available tools.
- Ollama translates intent into an agent-style shell plan.
- MXTerm applies local safety checks before execution.
- Dangerous commands can be blocked or require confirmation.

## Discoverability

Run `mxterm help` to see:

- the kinds of tasks MXTerm can handle
- example natural-language requests
- the current configured model
- useful commands for diagnostics, history, hooks, and model switching

## Model Management

MXTerm stores the active Ollama model in its config file.

- `mxterm model list` shows installed Ollama models and highlights the configured one
- `mxterm model current` prints the current configured model
- `mxterm model use <name>` switches MXTerm to another installed model
- `mxterm model use <name> --force` saves a model name even if Ollama is temporarily unavailable

## Safety

MXTerm ships with rule-based checks for:

- `rm -rf`
- `shutdown`, `reboot`
- `mkfs`, `dd`, `format`
- risky redirections to system paths
- chained or privileged commands

Current defaults are conservative:

- low-risk AI commands can run directly
- medium-risk commands require confirmation
- high-risk commands are blocked by default

Permission levels:

- `low`: every executable action requires confirmation; multi-step agent runs ask before each step
- `medium`: current balanced default; MXTerm confirms based on risk and route
- `high`: execute allowed commands immediately without confirmation prompts

MXTerm also writes JSONL execution logs under the platform-specific runtime directory, for example:

- Windows: `%LOCALAPPDATA%\\MXTerm\\logs\\mxterm.log.jsonl`
- macOS / Linux: `~/.local/state/MXTerm/logs/mxterm.log.jsonl` or the equivalent directory reported by `platformdirs`

## Shell Integration

- `zsh` installs a custom `accept-line` widget so pressing Enter can auto-capture unresolved input before `command not found`
- `bash` binds Enter through Readline with `bind -x`, while keeping `command_not_found_handle` as a fallback
- PowerShell uses PSReadLine Enter interception when available, with the `mx` alias as a fallback
- all generated hooks export session markers such as `MXTERM_HOOK_ACTIVE`, `MXTERM_HOOK_SHELL`, and `MXTERM_HOOK_AUTO_CAPTURE_MODE`
- `mxterm hooks doctor --shell <name>` checks both generated files and whether the current shell session actually loaded the MXTerm hook
- when MXTerm sends a natural-language request to Ollama, the shell hook shows the active model name and a loading spinner before the preview appears
- if Ollama returns no executable shell action, MXTerm asks the user to enter another request instead of emitting a fake command
- destructive delete requests can preview matching files before confirmation when MXTerm can resolve the targets locally
- all natural-language requests now run through the MXTerm agent layer
- `mxterm run` can execute agent plans step by step with local preflight checks, optional per-step confirmation, and retry-on-failure behavior
- commands that change session state, such as `cd`, run in the current shell session through generated hook code

## Configuration

MXTerm stores runtime files under the user config, data, and state directories reported by `platformdirs`.

Default config:

```toml
[ollama]
host = "http://127.0.0.1:11434"
model = "qwen3:8b"
timeout_seconds = 60

[shell]
preferred = "auto"
confirm_mode = "auto_low_risk" # auto_low_risk | always | never
auto_capture = true
auto_capture_mode = "smart"    # smart | natural_language | always
explicit_command = "mx"
show_banner = true

[safety]
dry_run = false
block_high_risk = true
preview_ai_commands = true
permission_level = "medium"

[agent]
enabled = true
max_steps = 5
preflight_checks = true
confirm_each_step = true
retry_on_failure = true
max_retries = 1
```

Auto-capture modes:

- `smart`: capture natural-language input and most unresolved multi-word lines
- `natural_language`: only capture clear natural-language requests
- `always`: aggressively send unresolved input to MXTerm first

Agent behavior:

- when `agent.enabled = true`, every natural-language request is translated through MXTerm's agent planner
- small requests usually produce one executable step plus a short plan summary
- larger requests can expand into multiple ordered shell steps, and MXTerm will require confirmation before execution
- `preflight_checks` verifies local commands and target directories before a multi-step plan starts
- `confirm_each_step` lets MXTerm ask before each step of a multi-step plan
- `retry_on_failure` and `max_retries` control local retry behavior for failed shell steps
- set `agent.enabled = false` if you want the older single-command translation path

Useful commands:

```bash
mxterm help
mxterm config path
mxterm config show --json
mxterm history
mxterm session
mxterm runtime
mxterm logs tail -n 20
mxterm model list
mxterm model current
mxterm model use qwen3:14b
mxterm permission current
mxterm permission use high
mxterm hooks refresh --shell zsh
mxterm hooks doctor --shell zsh
```

## One-Shot Usage

If you have not installed shell hooks yet, you can still use MXTerm directly:

```bash
mxterm run --shell powershell --cwd . --input "show files here" --yes
```

## Development

```bash
python -m pip install -e .[dev]
pytest
```

## Release Assets

The release helper scripts and workflows can:

- build PyInstaller binaries for macOS, Linux, and Windows
- package platform archives
- generate per-platform manifest files with size and SHA-256 checksum
- upload release assets and Python distributions on version tags

## Limitations

- `fish`, `nushell`, and `cmd.exe` are not part of the first release
- `zsh` and `bash` Enter interception depends on interactive shells with `zle` or `readline` support
- full PTY terminal emulation is out of scope for this version
- this README currently defaults to GitHub installation; after publishing to PyPI, you can switch back to `pipx install mxterm`
