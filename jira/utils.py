def extract_adf_text(adf: dict) -> str:
    """Extract plain text from an Atlassian Document Format (ADF) object."""
    paragraphs = adf.get("content", []) if adf else []
    return " ".join(
        item.get("text", "")
        for para in paragraphs
        for item in para.get("content", [])
        if item.get("type") == "text"
    )
