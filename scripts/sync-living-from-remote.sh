#!/usr/bin/env bash
# Rsync remote memory/living/ into this clone's memory/verified/ for IDE/git diff review.
# Override with env vars REMOTE and REMOTE_ROOT (see usage when both defaults apply).
set -euo pipefail

DEFAULT_REMOTE="root@bkr1.local"
DEFAULT_REMOTE_ROOT="/root/gitrepos/agentic-assistant"

using_default_remote=true
using_default_root=true
[[ -v REMOTE ]] && using_default_remote=false
[[ -v REMOTE_ROOT ]] && using_default_root=false

REMOTE="${REMOTE:-$DEFAULT_REMOTE}"
REMOTE_ROOT="${REMOTE_ROOT:-$DEFAULT_REMOTE_ROOT}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT_PATH="${REPO_ROOT}/scripts/$(basename "$0")"

echo "=== sync-living-from-remote ==="
echo "Action: rsync remote living memory -> local verified memory"
echo "  REMOTE       = ${REMOTE}"
echo "  REMOTE_ROOT  = ${REMOTE_ROOT}"
echo "  source       = ${REMOTE}:${REMOTE_ROOT}/memory/living/"
echo "  destination  = ${REPO_ROOT}/memory/verified/"
echo ""

if [[ "$using_default_remote" == true && "$using_default_root" == true ]]; then
  echo "Note: REMOTE and REMOTE_ROOT were not set in the environment; using defaults above."
  echo "To override, set them when invoking, for example:"
  echo "  REMOTE=user@host REMOTE_ROOT=/path/to/agentic-assistant \\"
  echo "    ${SCRIPT_PATH}"
  echo "Or: export REMOTE=... REMOTE_ROOT=... ; ${SCRIPT_PATH}"
  echo ""
fi

rsync -avz \
  -e "ssh -o BatchMode=yes" \
  "${REMOTE}:${REMOTE_ROOT}/memory/living/" \
  "${REPO_ROOT}/memory/verified/"

echo ""
echo "Done. Synced into: ${REPO_ROOT}/memory/verified/"
echo "Review in IDE / git diff; commit only what you want to keep."
