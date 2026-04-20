from pathlib import Path

MEMORY_BASE = Path(__file__).parent.parent / "memory"
VERIFIED_DIR = MEMORY_BASE / "verified"
LIVING_DIR   = MEMORY_BASE / "living"


def _load_md_files(directory: Path) -> dict[str, str]:
    result = {}
    if not directory.exists():
        return result
    for path in sorted(directory.rglob("*.md")):
        content = path.read_text().strip()
        if content:
            result[str(path.relative_to(directory))] = content
    return result


def build_prompt(context: dict) -> str:
    verified = _load_md_files(VERIFIED_DIR)
    living   = _load_md_files(LIVING_DIR)
    living_updates = {k: v for k, v in living.items() if v != verified.get(k, "")}

    parts = [
        "You are an experienced SBR (Storage-Based Remediation) engineer. "
        "Analyze the following Jira ticket using your domain knowledge and suggest next steps.",
        "## Ticket Details",
    ]
    for key, value in context.items():
        if value:
            parts.append(f"**{key.replace('_', ' ').title()}:** {value}")

    if verified:
        parts.append("## Verified Domain Knowledge")
        for name, content in verified.items():
            parts.append(f"### {name}\n{content}")

    if living_updates:
        parts.append("## Recent Agent Observations (Living Memory Updates)")
        for name, content in living_updates.items():
            parts.append(f"### {name}\n{content}")

    parts.append(
        "## Task\n"
        "Based on the ticket details and domain knowledge above, provide:\n"
        "1. A brief analysis of what this ticket is about (1-2 sentences)\n"
        "2. Suggested next steps or investigation areas\n"
        "Keep your response concise and actionable."
    )
    return "\n\n".join(parts)
