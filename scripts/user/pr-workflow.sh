#!/usr/bin/env bash
# Jira URL/key or GitHub PR URL → Vertex. No auto git commit/PR.
#
# Usage: scripts/user/pr-workflow.sh <JIRA_URL_OR_KEY|GITHUB_PR_URL> [-p] [-c TEXT] [-f FILE]
# Env: PR_WORKFLOW_CONTEXT_FILE (used when -f omitted)
# GitHub requires gh auth (same as scripts/user/pr-review.sh).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../lib/find_python.sh
source "$(dirname "${BASH_SOURCE[0]}")/../lib/find_python.sh"

die() { echo "pr-workflow: $*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Usage: scripts/user/pr-workflow.sh <JIRA_URL_OR_KEY|GITHUB_PR_URL> [-p] [-c TEXT] [-f FILE]
  -p, --prompt        Print prompt only (no Vertex call)
  -c, --context       Extra instructions for the agent prompt
  -f, --context-file  Read extra instructions from FILE
  PR_WORKFLOW_CONTEXT_FILE  Same as -f when -f omitted
EOF
}

[[ $# -ge 1 ]] || { usage; die "missing URL or issue key"; }

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
    -p|--prompt)
      PASS_ARGS+=(-p)
      shift
      ;;
    -c|--context)
      [[ $# -ge 2 ]] || die "missing value for $1"
      PASS_ARGS+=("$1" "$2")
      shift 2
      ;;
    -f|--context-file)
      [[ $# -ge 2 ]] || die "missing value for $1"
      PASS_ARGS+=("$1" "$2")
      shift 2
      ;;
    -*)
      die "unknown option: $1"
      ;;
    *)
      [[ -z "$TARGET" ]] || die "only one URL allowed"
      TARGET="$1"
      shift
      ;;
  esac
done

[[ -n "$TARGET" ]] || { usage; die "missing URL or issue key"; }

cd "$REPO_ROOT"
exec env PYTHONPATH="$REPO_ROOT" "$PY" -m agent.pr_workflow "${PASS_ARGS[@]}" "$TARGET"
