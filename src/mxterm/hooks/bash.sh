export MXTERM_HOOK_ACTIVE="1"
export MXTERM_HOOK_SHELL="bash"
export MXTERM_HOOK_AUTO_CAPTURE="__MXTERM_AUTO_CAPTURE__"
export MXTERM_HOOK_AUTO_CAPTURE_MODE="__MXTERM_AUTO_CAPTURE_MODE__"
export MXTERM_HOOK_EXPLICIT_COMMAND="__MXTERM_EXPLICIT_COMMAND__"

__mxterm_shell_resolves_token() {
  local token="$1"
  [[ -z "$token" ]] && return 1
  type -t -- "$token" >/dev/null 2>&1
}

__mxterm_first_token() {
  local line="${1#"${1%%[![:space:]]*}"}"
  line="${line%%[|&;<>]*}"
  printf '%s\n' "${line%%[[:space:]]*}"
}

__mxterm_dispatch_line() {
  local line="$1"
  local code
  code="$(command mxterm hook-dispatch --shell bash --cwd "$PWD" -- "$line")"
  local status=$?
  if [[ $status -eq 0 && -n "$code" ]]; then
    builtin eval -- "$code"
  fi
  return $status
}

__mxterm_looks_natural_language() {
  local line="$1"

  if printf '%s' "$line" | LC_ALL=C grep -q '[^ -~[:space:]]'; then
    return 0
  fi

  case "${line,,}" in
    *"?"*|*" please "*|please*|help*|show*|find*|list*|install*|start*|stop*|open*|why*|how*|create*|remove*|delete*|enter*|go\ to*|switch\ to*)
      return 0
      ;;
  esac

  return 1
}

__mxterm_should_auto_capture() {
  local line="$1"
  local mode="__MXTERM_AUTO_CAPTURE_MODE__"

  [[ "$mode" == "always" ]] && return 0

  if __mxterm_looks_natural_language "$line"; then
    return 0
  fi

  [[ "$mode" == "natural_language" ]] && return 1

  if [[ "$line" == *" "* || "$line" == *$'\t'* ]]; then
    return 0
  fi

  return 1
}

__MXTERM_EXPLICIT_COMMAND__() {
  local line="$*"
  [[ -z "${line//[[:space:]]/}" ]] && return 0
  builtin history -s -- "$line"
  __mxterm_dispatch_line "$line"
}

command_not_found_handle() {
  local line="$*"
  __mxterm_dispatch_line "$line"
  local status=$?
  if [[ $status -eq 0 ]]; then
    return 0
  fi
  printf 'bash: command not found: %s\n' "$1" >&2
  return 127
}

if [[ $- == *i* ]]; then
  if [[ "__MXTERM_AUTO_CAPTURE__" == "1" ]]; then
    __mxterm_accept_line() {
      local line="$READLINE_LINE"
      local first_token

      if [[ -z "${line//[[:space:]]/}" ]]; then
        printf '\n'
        READLINE_LINE=""
        READLINE_POINT=0
        return
      fi

      first_token="$(__mxterm_first_token "$line")"
      if __mxterm_shell_resolves_token "$first_token"; then
        printf '\n'
        builtin history -s -- "$line"
        builtin eval -- "$line"
        READLINE_LINE=""
        READLINE_POINT=0
        return
      fi

      if ! __mxterm_should_auto_capture "$line"; then
        printf '\n'
        builtin history -s -- "$line"
        builtin eval -- "$line"
        READLINE_LINE=""
        READLINE_POINT=0
        return
      fi

      printf '\n'
      builtin history -s -- "$line"
      __mxterm_dispatch_line "$line"
      READLINE_LINE=""
      READLINE_POINT=0
    }

    bind -x '"\C-m":__mxterm_accept_line'
    bind -x '"\C-j":__mxterm_accept_line'
  fi

  if [[ "__MXTERM_SHOW_BANNER__" == "1" ]]; then
    printf '[MXTerm] loaded for bash. Enter auto-capture: __MXTERM_AUTO_CAPTURE__ / mode=__MXTERM_AUTO_CAPTURE_MODE__. Use __MXTERM_EXPLICIT_COMMAND__ <text> for explicit AI mode.\n' >&2
  fi
fi
