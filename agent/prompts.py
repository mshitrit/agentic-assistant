from enum import Enum
from pathlib import Path

MEMORY_BASE = Path(__file__).parent.parent / "memory"
VERIFIED_DIR = MEMORY_BASE / "verified"
LIVING_DIR   = MEMORY_BASE / "living"


class AgentMode(Enum):
    JIRA         = "jira"
    SLACK        = "slack"
    SLACK_THREAD = "slack_thread"


def _load_md_files(directory: Path) -> dict[str, str]:
    result = {}
    if not directory.exists():
        return result
    for path in sorted(directory.rglob("*.md")):
        content = path.read_text().strip()
        if content:
            result[str(path.relative_to(directory))] = content
    return result


_TOOL_USE_INSTRUCTIONS = (
    "## Tool Use Instructions\n"
    "You have access to tools to read files from the operator repository and update living memory. "
    "Use them sparingly and purposefully:\n"
    "- Only read files you have a clear, specific reason to check based on the question. "
    "Do not explore the codebase speculatively.\n"
    "- Limit yourself to 3–5 files most directly relevant to the question.\n"
    "- If the verified domain knowledge already covers what you need, prefer it over reading source files.\n"
    "- If you detect that the current codebase either contradicts the verified domain knowledge "
    "or contains significant functionality not yet documented there, update the relevant file "
    "in living memory using `write_memory_file`. "
    "Include the full updated file content — not just the changed section. "
    "Only update what you have directly verified in code. Do not speculate."
)


def build_jira_prompt(context: dict, operator: str = "", op_name: str = "") -> str:
    verified_dir = (VERIFIED_DIR / operator) if operator else VERIFIED_DIR
    living_dir   = (LIVING_DIR / operator)   if operator else LIVING_DIR
    verified = _load_md_files(verified_dir)
    living   = _load_md_files(living_dir)
    living_updates = {k: v for k, v in living.items() if v != verified.get(k, "")}

    persona = f"You are an experienced {op_name} engineer. " if op_name else "You are an experienced engineer. "
    parts = [
        persona + "Analyze the following Jira ticket using your domain knowledge and suggest next steps.",
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

    parts.append(_TOOL_USE_INSTRUCTIONS)

    parts.append(
        "## Task\n"
        "Based on the ticket details and domain knowledge above, provide:\n"
        "1. A brief analysis of what this ticket is about (1-2 sentences)\n"
        "2. Suggested next steps or investigation areas\n"
        "Keep your response concise and actionable."
    )
    return "\n\n".join(parts)


def build_slack_prompt(question: str, operator: str = "", op_name: str = "") -> str:
    verified_dir = (VERIFIED_DIR / operator) if operator else VERIFIED_DIR
    living_dir   = (LIVING_DIR / operator)   if operator else LIVING_DIR
    verified = _load_md_files(verified_dir)
    living   = _load_md_files(living_dir)
    living_updates = {k: v for k, v in living.items() if v != verified.get(k, "")}

    persona = f"You are an experienced {op_name} engineer" if op_name else "You are an experienced engineer"
    parts = [
        persona + " answering a question from a colleague in Slack. Give a clear, direct answer. "
        "Keep it concise unless the question asks for detail. "
        "Format your response using Slack markup: "
        "*bold* for emphasis, `code` for commands or field names, plain bullet points with - for lists. "
        "Do not use Markdown headers (##) or double asterisks (**).",
        f"*Question:* {question}",
    ]

    if verified:
        parts.append("## Verified Domain Knowledge")
        for name, content in verified.items():
            parts.append(f"### {name}\n{content}")

    if living_updates:
        parts.append("## Recent Agent Observations (Living Memory Updates)")
        for name, content in living_updates.items():
            parts.append(f"### {name}\n{content}")

    parts.append(_TOOL_USE_INSTRUCTIONS)

    return "\n\n".join(parts)


def build_slack_thread_prompt(thread_history: str, operator: str = "", op_name: str = "") -> str:
    verified_dir = (VERIFIED_DIR / operator) if operator else VERIFIED_DIR
    living_dir   = (LIVING_DIR / operator)   if operator else LIVING_DIR
    verified = _load_md_files(verified_dir)
    living   = _load_md_files(living_dir)
    living_updates = {k: v for k, v in living.items() if v != verified.get(k, "")}

    persona = f"You are an experienced {op_name} engineer" if op_name else "You are an experienced engineer"
    parts = [
        persona + " continuing a conversation in Slack. The thread history below shows what has already been discussed. "
        "Answer the latest question in context of the prior exchange. "
        "Be concise and do not repeat what was already covered. "
        "Format your response using Slack markup: "
        "*bold* for emphasis, `code` for commands or field names, plain bullet points with - for lists. "
        "Do not use Markdown headers (##) or double asterisks (**).",
        f"*Thread history:*\n{thread_history}",
    ]

    if verified:
        parts.append("## Verified Domain Knowledge")
        for name, content in verified.items():
            parts.append(f"### {name}\n{content}")

    if living_updates:
        parts.append("## Recent Agent Observations (Living Memory Updates)")
        for name, content in living_updates.items():
            parts.append(f"### {name}\n{content}")

    parts.append(_TOOL_USE_INSTRUCTIONS)

    return "\n\n".join(parts)


def build_prompt(context: dict, mode: AgentMode = AgentMode.JIRA, operator: str = "", op_name: str = "") -> str:
    if mode == AgentMode.SLACK_THREAD:
        return build_slack_thread_prompt(context.get("title", ""), operator=operator, op_name=op_name)
    if mode == AgentMode.SLACK:
        return build_slack_prompt(context.get("title", ""), operator=operator, op_name=op_name)
    return build_jira_prompt(context, operator=operator, op_name=op_name)
