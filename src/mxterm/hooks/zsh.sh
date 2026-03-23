export MXTERM_HOOK_ACTIVE="1"
export MXTERM_HOOK_SHELL="zsh"
export MXTERM_HOOK_AUTO_CAPTURE="__MXTERM_AUTO_CAPTURE__"
export MXTERM_HOOK_AUTO_CAPTURE_MODE="__MXTERM_AUTO_CAPTURE_MODE__"
export MXTERM_HOOK_EXPLICIT_COMMAND="__MXTERM_EXPLICIT_COMMAND__"

__mxterm_shell_resolves_token() {
  local token="$1"
  [[ -z "$token" ]] && return 1
  whence -w -- "$token" >/dev/null 2>&1
}

__mxterm_first_token() {
  local line="${1#"${1%%[![:space:]]*}"}"
  local -a words
  words=(${(z)line})
  [[ ${#words[@]} -gt 0 ]] && print -r -- "${words[1]}"
}

__mxterm_dispatch_line() {
  local line="$1"
  local code
  code="$(command mxterm hook-dispatch --shell zsh --cwd "$PWD" -- "$line")"
  local status=$?
  if [[ $status -eq 0 && -n "$code" ]]; then
    eval "$code"
  fi
  return $status
}

__mxterm_looks_natural_language() {
  local line="$1"

  if printf '%s' "$line" | LC_ALL=C grep -q '[^ -~[:space:]]'; then
    return 0
  fi

  case "${line:l}" in
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
  print -sr -- "$line"
  __mxterm_dispatch_line "$line"
}

command_not_found_handler() {
  local line="$*"
  __mxterm_dispatch_line "$line"
  local status=$?
  if [[ $status -eq 0 ]]; then
    return 0
  fi
  print -u2 -- "zsh: command not found: $1"
  return 127
}

if [[ -o interactive ]]; then
  if [[ "__MXTERM_AUTO_CAPTURE__" == "1" ]]; then
    __mxterm_accept_line() {
      local line="$BUFFER"
      local first_token

      if [[ -z "${line//[[:space:]]/}" ]]; then
        zle .accept-line
        return
      fi

      first_token="$(__mxterm_first_token "$line")"
      if __mxterm_shell_resolves_token "$first_token"; then
        zle .accept-line
        return
      fi

      if ! __mxterm_should_auto_capture "$line"; then
        zle .accept-line
        return
      fi

      print
      print -sr -- "$line"
      __mxterm_dispatch_line "$line"
      local status=$?
      BUFFER=""
      CURSOR=0
      zle redisplay
      if [[ $status -ne 0 ]]; then
        zle -M "MXTerm did not execute the line."
      fi
    }

    zle -N __mxterm_accept_line
    bindkey '^M' __mxterm_accept_line
    bindkey '^J' __mxterm_accept_line
  fi

  if [[ "__MXTERM_SHOW_BANNER__" == "1" ]]; then
    print -P "%F{45}[MXTerm]%f loaded for zsh. Enter auto-capture: __MXTERM_AUTO_CAPTURE__ / mode=__MXTERM_AUTO_CAPTURE_MODE__. Use %B__MXTERM_EXPLICIT_COMMAND__%b <text> for explicit AI mode."
  fi
fi
