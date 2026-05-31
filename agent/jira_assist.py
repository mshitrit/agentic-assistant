"""CLI: one-shot Jira analysis to console (no Jira writes)."""

from __future__ import annotations

import argparse
import sys

from agent.claude import ask_agent
from agent.prompts import AgentMode, build_prompt
from config.settings import OPERATORS
from jira.client import get_issue_details
from jira.utils import build_agent_context, detect_operator, parse_jira_issue_key


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze a Jira issue and print AI output to console only",
    )
    parser.add_argument("target", help="Jira issue key or browse URL")
    parser.add_argument(
        "-p",
        "--prompt",
        action="store_true",
        help="Print prompt only (no Vertex call)",
    )
    parser.add_argument(
        "--internal",
        action="store_true",
        help="Include internal Jira comments in context (tagged as [internal])",
    )
    args = parser.parse_args(argv)

    issue_key = parse_jira_issue_key(args.target)
    if not issue_key:
        print("jira-assist: could not parse issue key", file=sys.stderr)
        return 1

    fields = get_issue_details(issue_key)
    if fields is None:
        print(f"jira-assist: failed to fetch {issue_key}", file=sys.stderr)
        return 1

    # Console-only mode never posts skip notices; fail closed on restricted tickets.
    if fields.get("security") is not None:
        print(
            "jira-assist: issue has a Jira security level; refusing external AI analysis",
            file=sys.stderr,
        )
        return 1

    operator = detect_operator(fields, OPERATORS)
    if not operator:
        print("jira-assist: no operator matches ticket components", file=sys.stderr)
        return 1

    repo_path = OPERATORS[operator].get("repo_path", "")
    op_name = OPERATORS[operator]["components"][0]

    all_comments = fields.get("comment", {}).get("comments", [])
    public_comments = fields.get("comment", {}).get("public_comments", [])
    comments = all_comments if args.internal else public_comments
    context = build_agent_context(
        fields,
        comments,
        mark_internal_comments=args.internal,
    )

    if args.prompt:
        print(build_prompt(context, AgentMode.JIRA, operator=operator, op_name=op_name))
        return 0

    result = ask_agent(
        context,
        mode=AgentMode.JIRA,
        operator=operator,
        op_name=op_name,
        repo_path=repo_path,
    )
    if not result.ok:
        print(f"jira-assist: {result.error}", file=sys.stderr)
        return 1

    print(result.response)
    return 0


if __name__ == "__main__":
    sys.exit(main())
