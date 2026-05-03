from enum import Flag, auto

config = {}
with open("jira_config.txt") as f:
    for line in f:
        key, _, value = line.strip().partition("=")
        config[key] = value

JIRA_USER   = config["JIRA_USER"]
JIRA_TOKEN  = config["JIRA_TOKEN"]
CLOUD_ID    = config["CLOUD_ID"]
ISSUE_KEY   = config.get("ISSUE_KEY", "").strip()
COMPONENTS  = [c.strip() for c in config.get("COMPONENTS", "").split(",") if c.strip()]
GCP_PROJECT = config["GCP_PROJECT_ID"]
GCP_REGION  = config["GCP_REGION"]
SBR_REPO_PATH = config.get("SBR_REPO_PATH", "").strip()

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
