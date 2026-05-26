from functools import wraps
import re

from jira.comments import format_issue_comments


def extract_adf_text(adf: dict) -> str:
    """Extract plain text from an Atlassian Document Format (ADF) object."""
    paragraphs = adf.get("content", []) if adf else []
    return " ".join(
        item.get("text", "")
        for para in paragraphs
        for item in para.get("content", [])
        if item.get("type") == "text"
    )


_ISSUE_KEY_RE = re.compile(r"([A-Z][A-Z0-9]+-\d+)")


def parse_jira_issue_key(url_or_key: str) -> str | None:
    """Return PROJ-123 from a browse URL or bare issue key."""
    s = (url_or_key or "").strip()
    if not s:
        return None
    if _ISSUE_KEY_RE.fullmatch(s):
        return s
    m = _ISSUE_KEY_RE.search(s)
    return m.group(1) if m else None


def build_agent_context(
    fields: dict, comments: list, *, mark_internal_comments: bool = False,
) -> dict:
    """Build the ask_agent context dict (same fields as main.py poller)."""
    return {
        "title": fields.get("summary"),
        "description": extract_adf_text(fields.get("description") or {}),
        "status": fields.get("status", {}).get("name"),
        "priority": fields.get("priority", {}).get("name"),
        "issue_type": fields.get("issuetype", {}).get("name"),
        "assignee": (fields.get("assignee") or {}).get("displayName"),
        "components": [c["name"] for c in fields.get("components", [])],
        "comments": format_issue_comments(comments, include_internal=mark_internal_comments),
    }


def detect_operator(fields: dict, operators: dict) -> str | None:
    """Return the operator key whose components match the ticket's components, or None."""
    ticket_components = {c["name"] for c in fields.get("components", [])}
    for op_key, op_config in operators.items():
        if ticket_components & set(op_config.get("components", [])):
            return op_key
    return None


def jira_request(fn):
    """Decorator that catches network/API errors, logs them, and returns None on failure."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            print(f"[ERROR] {fn.__name__} failed: {e}")
            return None
    return wrapper
