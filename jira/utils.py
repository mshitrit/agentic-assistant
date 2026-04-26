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
