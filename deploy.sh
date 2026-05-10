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

# ── 1b. Seed living memory from verified if living is empty ───────────────────
LIVING_ROOT="memory/living"
VERIFIED_ROOT="memory/verified"
if [ ! -d "$VERIFIED_ROOT" ]; then
    echo "Warning: $VERIFIED_ROOT missing; skip living memory seed."
elif [ ! -d "$LIVING_ROOT" ] || [ -z "$(ls -A "$LIVING_ROOT" 2>/dev/null)" ]; then
    mkdir -p "$LIVING_ROOT"
    cp -a "$VERIFIED_ROOT"/. "$LIVING_ROOT"/
    echo "Living memory was empty; copied verified memory into $LIVING_ROOT"
fi

# ── 2. Update operator repos (if configured) ─────────────────────────────────
while IFS='=' read -r key value; do
    [[ "$key" =~ ^OPERATOR_.*_REPO_PATH$ ]] || continue
    value=$(echo "$value" | tr -d '[:space:]')
    [ -n "$value" ] && [ -d "$value" ] || continue
    echo "Pulling latest changes in operator repo at $value..."
    git -C "$value" pull origin main
    echo "Done."
done < config/config.txt

# ── 3. Stop running processes ─────────────────────────────────────────────────
echo "Stopping any running agent processes..."
pkill -f "$PYTHON main.py" 2>/dev/null         || true
pkill -f "$PYTHON slack_bot_main.py" 2>/dev/null || true
sleep 1

# ── 4. Start selected processes ───────────────────────────────────────────────
if [[ "$MODE" == "jira" || "$MODE" == "both" ]]; then
    MAIN_LOG="logs/main_${TIMESTAMP}.log"
    echo "Starting Jira poller... logging to $MAIN_LOG"
    nohup env PYTHONUNBUFFERED=1 $PYTHON main.py > "$MAIN_LOG" 2>&1 &
    echo "Jira poller started. PID: $!"
fi

if [[ "$MODE" == "slack" || "$MODE" == "both" ]]; then
    SLACK_LOG="logs/slack_bot_${TIMESTAMP}.log"
    echo "Starting Slack bot... logging to $SLACK_LOG"
    nohup env PYTHONUNBUFFERED=1 $PYTHON slack_bot_main.py > "$SLACK_LOG" 2>&1 &
    echo "Slack bot started. PID: $!"
fi

echo "Deployment complete."

if [[ "$MODE" == "jira" ]]; then
    echo "Following $MAIN_LOG (Ctrl+C to stop)..."
    tail -f "$MAIN_LOG"
elif [[ "$MODE" == "slack" ]]; then
    echo "Following $SLACK_LOG (Ctrl+C to stop)..."
    tail -f "$SLACK_LOG"
else
    echo "Following $MAIN_LOG and $SLACK_LOG (Ctrl+C to stop)..."
    tail -f "$MAIN_LOG" "$SLACK_LOG"
fi
