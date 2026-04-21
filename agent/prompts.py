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
        "## Tool Use Instructions\n"
        "You have access to tools to read files from the SBR repository and update living memory. "
        "Use them sparingly and purposefully:\n"
        "- Only read files you have a clear, specific reason to check based on the ticket. "
        "Do not explore the codebase speculatively.\n"
        "- Limit yourself to 3–5 files most directly relevant to the ticket.\n"
        "- If the verified domain knowledge already covers what you need, prefer it over reading source files.\n"
        "- If you detect that the current codebase either contradicts the verified domain knowledge "
        "or contains significant functionality not yet documented there, update the relevant file "
        "in living memory using `write_memory_file`. "
        "Include the full updated file content — not just the changed section. "
        "Only update what you have directly verified in code. Do not speculate."
    )

    parts.append(
        "## Task\n"
        "Based on the ticket details and domain knowledge above, provide:\n"
        "1. A brief analysis of what this ticket is about (1-2 sentences)\n"
        "2. Suggested next steps or investigation areas\n"
        "Keep your response concise and actionable."
    )
    return "\n\n".join(parts)
