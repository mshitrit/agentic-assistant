import re
from enum import Flag, auto
from pathlib import Path

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

# Slack: accept tags for every operator with verified memory (subdirs of memory/verified).
_VERIFIED_MEMORY_ROOT = Path(__file__).resolve().parent.parent / "memory" / "verified"


def _slack_operator_tags_from_verified_memory() -> frozenset[str]:
    if not _VERIFIED_MEMORY_ROOT.is_dir():
        return frozenset()
    return frozenset(
        p.name.lower()
        for p in _VERIFIED_MEMORY_ROOT.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


_tags_from_memory = _slack_operator_tags_from_verified_memory()
SLACK_OPERATOR_TAGS: frozenset[str] = (
    _tags_from_memory if _tags_from_memory else frozenset(OPERATORS.keys())
)

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
