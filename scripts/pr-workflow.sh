#!/usr/bin/env bash
# Jira URL/key or GitHub PR URL → Vertex. No auto git commit/PR.
#
# Usage: scripts/pr-workflow.sh <JIRA_URL_OR_KEY|GITHUB_PR_URL> [-p]
# GitHub requires gh auth (same as scripts/pr-review.sh).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/find_python.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/find_python.sh"

die() { echo "pr-workflow: $*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Usage: scripts/pr-workflow.sh <JIRA_URL_OR_KEY|GITHUB_PR_URL> [-p]
  -p, --prompt   Print prompt only (no Vertex call)
EOF
}

[[ $# -ge 1 ]] || { usage; die "missing URL or issue key"; }

PY="$(find_python)"
[[ -n "$PY" ]] || die "python3 not found"

ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    -p|--prompt) ARGS+=(-p); shift ;;
    -*) die "unknown option: $1" ;;
    *)
      [[ ${#ARGS[@]} -eq 0 ]] || die "only one URL allowed"
      ARGS+=("$1")
      shift
      ;;
  esac
done

cd "$REPO_ROOT"
exec env PYTHONPATH="$REPO_ROOT" "$PY" -m agent.pr_workflow "${ARGS[@]}"
