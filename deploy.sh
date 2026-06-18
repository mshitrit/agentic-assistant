#!/bin/bash

set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

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
CONFIG="$REPO_ROOT/config/config.txt"
DEPLOY_BRANCH="main"
if [[ -f "$CONFIG" ]]; then
    while IFS='=' read -r key value; do
        [[ "$key" == DEPLOY_GIT_BRANCH ]] || continue
        value="${value#"${value%%[![:space:]]*}"}"
        value="${value%"${value##*[![:space:]]}"}"
        [[ -n "$value" ]] && DEPLOY_BRANCH="$value"
        break
    done < <(grep -E '^DEPLOY_GIT_BRANCH=' "$CONFIG" || true)
fi

GIT_REMOTE="origin"
echo "Aligning repo to $GIT_REMOTE/$DEPLOY_BRANCH (hard reset)..."
git -C "$REPO_ROOT" fetch "$GIT_REMOTE" "$DEPLOY_BRANCH"
git -C "$REPO_ROOT" checkout -B "$DEPLOY_BRANCH" "$GIT_REMOTE/$DEPLOY_BRANCH"
git -C "$REPO_ROOT" reset --hard "$GIT_REMOTE/$DEPLOY_BRANCH"
echo "Git sync complete (at $(git -C "$REPO_ROOT" rev-parse --short HEAD))."

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
bash "$REPO_ROOT/scripts/internal/update-operator-repos.sh"
echo "Operator repo sync complete; see logs/operator-repos-sync.log"

# ── 2b. Daily cron: operator repos at 02:00 (replaces prior entry with same id) ─
CRON_TAG="AGENTIC_CRON_JOB=operator_repo_sync"
CRON_LINE="0 2 * * * cd \"$REPO_ROOT\" && exec env $CRON_TAG /usr/bin/env bash \"$REPO_ROOT/scripts/internal/update-operator-repos.sh\""
if command -v crontab &>/dev/null; then
    _cron_tmp="$(mktemp)"
    ( crontab -l 2>/dev/null | grep -vF "$CRON_TAG" || true ) >"$_cron_tmp"
    echo "$CRON_LINE" >>"$_cron_tmp"
    crontab "$_cron_tmp"
    rm -f "$_cron_tmp"
    echo "Cron: daily 02:00 operator repo sync installed (id: $CRON_TAG)."
else
    echo "Warning: crontab not found; skipping daily operator repo sync schedule."
fi

# ── 3. Stop running processes ─────────────────────────────────────────────────
PID_FILE="$REPO_ROOT/agentic_assistant.pid"
echo "Stopping any running agent processes..."
if [ -f "$PID_FILE" ]; then
    while read -r pid; do
        if [ -n "$pid" ]; then
            kill "$pid" 2>/dev/null || true
        fi
    done < "$PID_FILE"
    sleep 1
fi

# ── 4. Start selected processes ───────────────────────────────────────────────
# Clear PID file before starting new processes
> "$PID_FILE"

if [[ "$MODE" == "jira" || "$MODE" == "both" ]]; then
    MAIN_LOG="logs/main_${TIMESTAMP}.log"
    echo "Starting Jira poller... logging to $MAIN_LOG"
    nohup env PYTHONUNBUFFERED=1 $PYTHON main.py > "$MAIN_LOG" 2>&1 &
    JIRA_PID=$!
    echo "$JIRA_PID" >> "$PID_FILE"
    echo "Jira poller started. PID: $JIRA_PID"
fi

if [[ "$MODE" == "slack" || "$MODE" == "both" ]]; then
    SLACK_LOG="logs/slack_bot_${TIMESTAMP}.log"
    echo "Starting Slack bot... logging to $SLACK_LOG"
    nohup env PYTHONUNBUFFERED=1 $PYTHON slack_bot_main.py > "$SLACK_LOG" 2>&1 &
    SLACK_PID=$!
    echo "$SLACK_PID" >> "$PID_FILE"
    echo "Slack bot started. PID: $SLACK_PID"
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
