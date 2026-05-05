from functools import wraps


def extract_adf_text(adf: dict) -> str:
    """Extract plain text from an Atlassian Document Format (ADF) object."""
    paragraphs = adf.get("content", []) if adf else []
    return " ".join(
        item.get("text", "")
        for para in paragraphs
        for item in para.get("content", [])
        if item.get("type") == "text"
    )


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
