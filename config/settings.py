import re
from enum import Flag, auto

config = {}
with open("config/config.txt") as f:
    for line in f:
        key, _, value = line.strip().partition("=")
        config[key] = value

JIRA_USER   = config["JIRA_USER"]
JIRA_TOKEN  = config["JIRA_TOKEN"]
CLOUD_ID    = config["CLOUD_ID"]
ISSUE_KEY   = config.get("ISSUE_KEY", "").strip()
GCP_PROJECT = config["GCP_PROJECT_ID"]
GCP_REGION  = config["GCP_REGION"]
# Vertex Claude model (pr-review.sh, pr-workflow.sh, Jira poller, Slack).
AGENT_MODEL = config.get("AGENT_MODEL", "claude-opus-4-5")
# pr-review.sh (agent/pr_review.py, non-streaming).
PR_REVIEW_MAX_TOKENS = int(config.get("PR_REVIEW_MAX_TOKENS", "8192"))
# pr-workflow.sh tool loop (agent/claude.py, streaming).
PR_WORKFLOW_MAX_TOKENS = int(config.get("PR_WORKFLOW_MAX_TOKENS", "32768"))

OPERATORS: dict[str, dict] = {}
for _k, _v in config.items():
    _m = re.match(r"^OPERATOR_(\w+)_COMPONENTS$", _k)
    if _m:
        _op = _m.group(1).lower()
        OPERATORS.setdefault(_op, {})["components"] = [c.strip() for c in _v.split(",") if c.strip()]
for _k, _v in config.items():
    _m = re.match(r"^OPERATOR_(\w+)_REPO_PATH$", _k)
    if _m:
        _op = _m.group(1).lower()
        OPERATORS.setdefault(_op, {})["repo_path"] = _v.strip()

POLL_INTERVAL   = 60
AI_PREFIX       = "🤖 [AI Generated]\n\n"
TRIGGER_LABEL   = "ai-assist"
TRIGGER_COMMENT = "/ai-assist"


class DebugMode(Flag):
    PRODUCTION   = 0
    DISABLE_JIRA = auto()  # print comments to console instead of posting to Jira
    DISABLE_AI   = auto()  # skip Claude call, use a hardcoded response instead
    FULL_DISABLE = DISABLE_JIRA | DISABLE_AI

MAX_READ_CALLS  = int(config.get("MAX_READ_CALLS", "10"))
MAX_WRITE_CALLS = int(config.get("MAX_WRITE_CALLS", "3"))
DEBUG_MODE = DebugMode[config.get("DEBUG_MODE", "PRODUCTION")]
LOG_LEVEL  = config.get("LOG_LEVEL", "INFO").upper()
SLACK_BOT_TOKEN = config.get("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN = config.get("SLACK_APP_TOKEN", "")
