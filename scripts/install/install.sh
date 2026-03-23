#!/usr/bin/env sh
set -eu

PACKAGE_REF="${PACKAGE_REF:-mxterm}"
TARGET_SHELL="${MXTERM_SHELL:-auto}"

if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
  echo "Python is required to install MXTerm." >&2
  exit 1
fi

if ! command -v pipx >/dev/null 2>&1; then
  echo "pipx not found. Installing pipx via python -m pip --user pipx" >&2
  if command -v python3 >/dev/null 2>&1; then
    python3 -m pip install --user pipx
  else
    python -m pip install --user pipx
  fi
fi

if ! command -v ollama >/dev/null 2>&1; then
  echo "Warning: Ollama is not on PATH. MXTerm can install, but AI translation will not work until Ollama is installed and running." >&2
fi

pipx install "$PACKAGE_REF" --force
mxterm config init >/dev/null 2>&1 || true
mxterm install --shell "$TARGET_SHELL"
echo "MXTerm installed. Restart your shell or source your profile."
