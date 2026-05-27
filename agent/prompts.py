from enum import Enum
from pathlib import Path

MEMORY_BASE = Path(__file__).parent.parent / "memory"
VERIFIED_DIR = MEMORY_BASE / "verified"
LIVING_DIR   = MEMORY_BASE / "living"


class AgentMode(Enum):
    JIRA         = "jira"
    SLACK        = "slack"
    SLACK_THREAD = "slack_thread"
    PR_WORKFLOW_JIRA = "pr_workflow_jira"
    PR_WORKFLOW_GITHUB = "pr_workflow_github"


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


_PR_WORKFLOW_INSTRUCTIONS = (
    "## Tool Use Instructions\n"
    "Prefer verified memory; read source when needed. When code must change, use `write_repo_file` "
    "with full file contents. Use `write_memory_file` only when code contradicts verified docs. "
    "Do not run git."
)

_PR_WORKFLOW_COMPLETION = (
    "## Completion\n"
    "Before your final message, decide:\n"
    "- **Code changes required:** call `write_repo_file` for every file to edit, then end with a "
    "line exactly `OUTCOME: implement`, then PR title + bullets and list files changed.\n"
    "- **No code change required** (won't fix, duplicate, needs info, not in this repo, etc.): do "
    "not call `write_repo_file`; end with a line exactly `OUTCOME: no_code_change` and a brief reason.\n"
    "Do not commit, push, open PRs, resolve review threads, or post PR comments."
)


def parse_workflow_outcome(text: str) -> str | None:
    """Return 'implement', 'no_code_change', or None if no OUTCOME line in agent text."""
    for line in (text or "").splitlines():
        s = line.strip().upper()
        if s == "OUTCOME: IMPLEMENT":
            return "implement"
        if s == "OUTCOME: NO_CODE_CHANGE":
            return "no_code_change"
    return None


def _operator_memory_sections(operator: str) -> list[str]:
    """Verified and living memory blocks for an operator (shared by Jira and PR prompts)."""
    verified_dir = VERIFIED_DIR / operator if operator else VERIFIED_DIR
    living_dir = LIVING_DIR / operator if operator else LIVING_DIR
    verified = _load_md_files(verified_dir)
    living = _load_md_files(living_dir)
    living_updates = {k: v for k, v in living.items() if v != verified.get(k, "")}
    parts: list[str] = []
    if verified:
        parts.append("## Verified Domain Knowledge")
        for name, content in verified.items():
            parts.append(f"### {name}\n{content}")
    if living_updates:
        parts.append("## Recent Agent Observations (Living Memory Updates)")
        for name, content in living_updates.items():
            parts.append(f"### {name}\n{content}")
    return parts


def build_jira_prompt(context: dict, operator: str = "", op_name: str = "") -> str:
    persona = f"You are an experienced {op_name} engineer. " if op_name else "You are an experienced engineer. "
    parts = [
        persona + "Analyze the following Jira ticket using your domain knowledge and suggest next steps.",
        "## Ticket Details",
    ]
    for key, value in context.items():
        if value:
            parts.append(f"**{key.replace('_', ' ').title()}:** {value}")

    parts.extend(_operator_memory_sections(operator))

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


def build_prompt(
    context: dict,
    mode: AgentMode = AgentMode.JIRA,
    operator: str = "",
    op_name: str = "",
    *,
    repo_path: str = "",
    base_branch: str = "main",
    branch_name: str = "",
) -> str:
    if mode == AgentMode.SLACK_THREAD:
        return build_slack_thread_prompt(context.get("title", ""), operator=operator, op_name=op_name)
    if mode == AgentMode.SLACK:
        return build_slack_prompt(context.get("title", ""), operator=operator, op_name=op_name)
    if mode == AgentMode.PR_WORKFLOW_JIRA:
        persona = f"You are an experienced {op_name} engineer." if op_name else "You are an experienced engineer."
        parts = [
            persona + " Implement a fix for the Jira ticket and prepare a pull request.",
            f"**Operator repo:** `{repo_path}`",
            f"**Suggested branch:** `{branch_name}`",
            "## Jira Ticket",
        ]
        for key, value in context.items():
            if value:
                parts.append(f"**{key.replace('_', ' ').title()}:** {value}")
        parts.extend(_operator_memory_sections(operator))
        parts.append(_PR_WORKFLOW_INSTRUCTIONS)
        parts.append(
            "## Task\n"
            "1. Plan the minimal correct fix.\n"
            "2. If changes are needed, apply them with `write_repo_file`.\n"
            "3. Follow **Completion** below."
        )
        parts.append(_PR_WORKFLOW_COMPLETION)
        return "\n\n".join(parts)
    # GitHub PR workflow: unresolved threads + diff (not the review rubric).
    if mode == AgentMode.PR_WORKFLOW_GITHUB:
        persona = f"You are an experienced {op_name} engineer." if op_name else "You are an experienced engineer."
        parts = [
            persona + " Address unresolved review feedback on an open GitHub pull request.",
            f"**Operator repo:** `{repo_path}`",
            f"**Base branch:** `{base_branch}`",
            f"**PR head branch:** `{branch_name}`",
            "## Pull request",
        ]
        for key, value in context.items():
            if value:
                parts.append(f"**{key.replace('_', ' ').title()}:** {value}")
        parts.extend(_operator_memory_sections(operator))
        parts.append(_PR_WORKFLOW_INSTRUCTIONS)
        parts.append(
            "## Task\n"
            "1. For each unresolved review thread, decide if a code change is required.\n"
            "2. If changes are needed, apply them with `write_repo_file`.\n"
            "3. Follow **Completion** below."
        )
        parts.append(_PR_WORKFLOW_COMPLETION)
        return "\n\n".join(parts)
    return build_jira_prompt(context, operator=operator, op_name=op_name)


PR_REVIEW_RUBRIC = """\
You are performing a thorough code review of a pull/merge request.

Review the provided diff (same as the hosting platform "Files changed" / "Changes" tab).
The merge target branch is stated in the request header when available.

Structure your review exactly as:

## Summary
(2-4 sentences: what the change does)

## Correctness
(Logic bugs, edge cases, error handling. Label each finding: Blocker, Major, Minor)

## Design
(Structure, separation of concerns, consistency with existing patterns)

## Tests
(Missing or weak coverage)

## Nits
(Style, naming, docs; non-blocking)

Each finding MUST cite file path and line number(s) when possible.
"""


def pr_review_rubric() -> str:
    return PR_REVIEW_RUBRIC


def build_pr_review_prompt(
    *,
    platform: str,
    reference: str,
    url: str = "",
    title: str = "",
    target_branch: str = "",
    source_branch: str = "",
    meta_json: str = "",
    diff: str = "",
    extra_context: str = "",
) -> str:
    parts = [
        PR_REVIEW_RUBRIC,
        "---",
        "## Request",
        f"- **Platform:** {platform}",
        f"- **Reference:** {reference}",
    ]
    if url:
        parts.append(f"- **URL:** {url}")
    if title:
        parts.append(f"- **Title:** {title}")
    if target_branch:
        parts.append(f"- **Merge target branch:** {target_branch}")
    if source_branch:
        parts.append(f"- **Source branch:** {source_branch}")

    parts.append(f"\n### Metadata (JSON)\n\n```json\n{meta_json}\n```\n")
    if extra_context:
        parts.append(f"### Additional context\n\n{extra_context}\n")
    parts.append(f"### Diff\n\n```diff\n{diff}\n```")
    return "\n\n".join(parts)
