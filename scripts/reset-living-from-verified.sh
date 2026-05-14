#!/usr/bin/env bash
# Replace memory/living/ with a copy of memory/verified/ (run after promoting changes to verified).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VER="${REPO_ROOT}/memory/verified"
LIV="${REPO_ROOT}/memory/living"

echo "=== reset-living-from-verified ==="
echo "Action: mirror verified -> living (rsync with --delete)"
echo "  source       = ${VER}/"
echo "  destination  = ${LIV}/"
echo ""

if [[ ! -d "$VER" ]]; then
  echo "Error: ${VER} does not exist." >&2
  exit 1
fi

mkdir -p "$LIV"
rsync -a --delete "${VER}/" "${LIV}/"

echo "Done. Living memory now matches verified under: ${LIV}/"
