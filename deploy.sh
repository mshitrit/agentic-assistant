#!/bin/bash

set -e

# ── Usage ────────────────────────────────────────────────────────────────────
usage() {
    echo "Usage: $0 [jira|slack|both]"
    echo ""
    echo "  jira   Start the Jira poller (main.py)"
    echo "  slack  Start the Slack bot (slack_bot_main.py)"
    echo "  both   Start both"
    exit 1
}

if [ $# -lt 1 ]; then
    echo "Error: missing required argument."
    usage
fi

MODE="$1"
if [[ "$MODE" != "jira" && "$MODE" != "slack" && "$MODE" != "both" ]]; then
    echo "Error: invalid argument '$MODE'."
    usage
fi

# ── Python auto-detect ────────────────────────────────────────────────────────
if command -v python3.11 &>/dev/null; then
    PYTHON="python3.11"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    echo "Error: no Python interpreter found (tried python3.11, python3, and python)."
    exit 1
fi
echo "Using Python: $PYTHON"

# ── Logs directory ────────────────────────────────────────────────────────────
mkdir -p logs
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ── 1. Update this repo ───────────────────────────────────────────────────────
echo "Pulling latest changes from Git..."
git pull
echo "Git pull complete."

# ── 2. Update SBR repo (if configured) ───────────────────────────────────────
SBR_REPO_PATH=$(grep -m1 "^SBR_REPO_PATH=" config/config.txt 2>/dev/null | cut -d'=' -f2- | tr -d '[:space:]')
if [ -n "$SBR_REPO_PATH" ] && [ -d "$SBR_REPO_PATH" ]; then
    echo "Pulling latest changes in SBR repo at $SBR_REPO_PATH..."
    git -C "$SBR_REPO_PATH" pull origin main
    echo "SBR repo pull complete."
else
    echo "SBR_REPO_PATH not set or not found, skipping SBR repo update."
fi

# ── 3. Stop running processes ─────────────────────────────────────────────────
echo "Stopping any running agent processes..."
pkill -f "$PYTHON main.py" 2>/dev/null         || true
pkill -f "$PYTHON slack_bot_main.py" 2>/dev/null || true
sleep 1

# ── 4. Start selected processes ───────────────────────────────────────────────
if [[ "$MODE" == "jira" || "$MODE" == "both" ]]; then
    LOG_FILE="logs/main_${TIMESTAMP}.log"
    echo "Starting Jira poller... logging to $LOG_FILE"
    nohup $PYTHON main.py > "$LOG_FILE" 2>&1 &
    echo "Jira poller started. PID: $!"
fi

if [[ "$MODE" == "slack" || "$MODE" == "both" ]]; then
    LOG_FILE="logs/slack_bot_${TIMESTAMP}.log"
    echo "Starting Slack bot... logging to $LOG_FILE"
    nohup $PYTHON slack_bot_main.py > "$LOG_FILE" 2>&1 &
    echo "Slack bot started. PID: $!"
fi

echo "Deployment complete."
