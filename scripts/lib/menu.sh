#!/usr/bin/env bash
# Shared helpers for agentic-assist-menu.sh

prompt_yes_no() {
  local prompt="$1"
  local default="${2:-n}"
  local hint="[y/N]"
  [[ "$default" == "y" ]] && hint="[Y/n]"
  local answer
  read -r -p "$prompt $hint: " answer
  answer="${answer:-$default}"
  [[ "$answer" =~ ^[Yy] ]]
}

prompt_optional() {
  local prompt="$1"
  local default="${2:-}"
  local answer
  if [[ -n "$default" ]]; then
    read -r -p "$prompt [$default]: " answer
    echo "${answer:-$default}"
  else
    read -r -p "$prompt (Enter for default): " answer
    echo "$answer"
  fi
}

prompt_required() {
  local prompt="$1"
  local answer
  while true; do
    read -r -p "$prompt: " answer
    if [[ -n "${answer// /}" ]]; then
      echo "$answer"
      return 0
    fi
    echo "Value required." >&2
  done
}

# Read optional multi-line input; empty line ends entry. Sets variable named by first arg.
prompt_multiline_optional() {
  local -n _out="$1"
  local prompt="$2"
  local line buf=""
  _out=""
  echo "$prompt" >&2
  echo "(Enter an empty line when done, or press Enter immediately to skip)" >&2
  while IFS= read -r line; do
    [[ -z "$line" ]] && break
    buf+="${line}"$'\n'
  done
  _out="${buf%$'\n'}"
}
