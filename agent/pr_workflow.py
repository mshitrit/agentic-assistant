"""CLI: Jira ticket → Vertex PR workflow (phase 1)."""

from __future__ import annotations

import argparse
import re
import sys

from agent.claude import ask_agent
from agent.prompts import AgentMode, build_prompt
from config.settings import OPERATORS, PR_WORKFLOW_BASE_BRANCH
from jira.client import get_issue_details
from jira.utils import build_agent_context, detect_operator, parse_jira_issue_key


def _suggested_branch(issue_key: str, summary: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", (summary or "").lower()).strip("-")[:40]
    return f"jira/{issue_key}" + (f"-{slug}" if slug else "")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PR workflow from a Jira ticket (phase 1)")
    parser.add_argument("jira_url", help="Jira browse URL or issue key")
    parser.add_argument("-p", "--prompt", action="store_true", help="Print prompt only")
    args = parser.parse_args(argv)

    issue_key = parse_jira_issue_key(args.jira_url)
    if not issue_key:
        print("pr-workflow: could not parse issue key", file=sys.stderr)
        return 1

    fields = get_issue_details(issue_key)
    if fields is None:
        print(f"pr-workflow: failed to fetch {issue_key}", file=sys.stderr)
        return 1

    operator = detect_operator(fields, OPERATORS)
    if not operator:
        print("pr-workflow: no operator matches ticket components", file=sys.stderr)
        return 1
    repo_path = OPERATORS[operator].get("repo_path", "")
    if not repo_path:
        print(f"pr-workflow: OPERATOR_{operator.upper()}_REPO_PATH not set", file=sys.stderr)
        return 1
    op_name = OPERATORS[operator]["components"][0]

    all_comments = fields.get("comment", {}).get("comments", [])
    context = build_agent_context(fields, all_comments, mark_internal_comments=True)
    branch = _suggested_branch(issue_key, context.get("title") or "")

    if args.prompt:
        print(build_prompt(
            context,
            AgentMode.PR_WORKFLOW_JIRA,
            operator=operator,
            op_name=op_name,
            repo_path=repo_path,
            base_branch=PR_WORKFLOW_BASE_BRANCH,
            branch_name=branch,
        ))
        return 0

    result = ask_agent(
        context,
        mode=AgentMode.PR_WORKFLOW_JIRA,
        repo_path=repo_path,
        operator=operator,
        op_name=op_name,
        base_branch=PR_WORKFLOW_BASE_BRANCH,
        branch_name=branch,
    )
    if not result.ok:
        print(f"pr-workflow: {result.error}", file=sys.stderr)
        return 1

    print(result.response)
    print("\n--- Next steps (operator repo; not run automatically) ---")
    print(f"  cd {repo_path}")
    print(f"  git fetch origin && git checkout -B {branch} origin/{PR_WORKFLOW_BASE_BRANCH}")
    print("  git status && git add ... && git commit && git push -u origin HEAD && gh pr create --fill")
    return 0


if __name__ == "__main__":
    sys.exit(main())
