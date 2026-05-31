#!/usr/bin/env bash
# Pull latest for every OPERATOR_*_REPO_PATH in config/config.txt (same logic as deploy).
# Logs to logs/operator-repos-sync.log with day-level timestamps.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG="$ROOT/config/config.txt"
LOG_DIR="$ROOT/logs"
LOG_FILE="$LOG_DIR/operator-repos-sync.log"
mkdir -p "$LOG_DIR"

ts() { date '+%Y-%m-%d %H:%M:%S %Z'; }

{
  echo "[$(ts)] === operator repo sync start ==="
  while IFS='=' read -r key value; do
    [[ "$key" =~ ^OPERATOR_.*_REPO_PATH$ ]] || continue
    value=$(echo "$value" | tr -d '[:space:]')
    if [[ -z "$value" ]] || [[ ! -d "$value" ]]; then
      echo "[$(ts)] SKIP $key (empty or not a directory): ${value:-<empty>}"
      continue
    fi
    echo "[$(ts)] PULL $key -> $value"
    git -C "$value" pull origin main
    echo "[$(ts)] OK   $value"
  done < "$CONFIG"
  echo "[$(ts)] === operator repo sync end ==="
} >>"$LOG_FILE" 2>&1
