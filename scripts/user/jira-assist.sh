#!/usr/bin/env bash
# One-shot Jira analysis to console (no Jira comments/updates).
#
# Usage: scripts/user/jira-assist.sh <JIRA_URL_OR_KEY> [-p] [--internal]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../lib/find_python.sh
source "$(dirname "${BASH_SOURCE[0]}")/../lib/find_python.sh"

die() { echo "jira-assist: $*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Usage: scripts/user/jira-assist.sh <JIRA_URL_OR_KEY> [-p] [--internal] [-c TEXT] [-f FILE]
  -p, --prompt        Print prompt only (no Vertex call)
      --internal      Include internal comments in context
  -c, --context       Extra instructions for the agent prompt
  -f, --context-file  Read extra instructions from FILE
EOF
}

[[ $# -ge 1 ]] || { usage; die "missing Jira URL or issue key"; }

PY="$(find_python)"
[[ -n "$PY" ]] || die "python3 not found"

TARGET=""
PASS_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    -p|--prompt|--internal)
      PASS_ARGS+=("$1")
      shift
      ;;
    -c|--context)
      PASS_ARGS+=(-c "$2")
      shift 2
      ;;
    -f|--context-file)
      PASS_ARGS+=(-f "$2")
      shift 2
      ;;
    -*)
      die "unknown option: $1"
      ;;
    *)
      [[ -z "$TARGET" ]] || die "only one Jira target allowed"
      TARGET="$1"
      shift
      ;;
  esac
done

[[ -n "$TARGET" ]] || { usage; die "missing Jira URL or issue key"; }

cd "$REPO_ROOT"
exec env PYTHONPATH="$REPO_ROOT" "$PY" -m agent.jira_assist "${PASS_ARGS[@]}" "$TARGET"
