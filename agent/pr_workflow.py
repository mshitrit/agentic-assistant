"""CLI: Jira ticket or GitHub PR URL → Vertex PR workflow."""

from __future__ import annotations

import argparse
import re
import sys

from agent.claude import ask_agent
from agent.prompts import AgentMode, build_prompt, parse_workflow_outcome
from config.settings import OPERATORS
from github.pr import (
    fetch_for_review,
    fetch_unresolved_threads,
    find_operator_for_github_repo,
    parse_github_pr_url,
)
from jira.client import get_issue_details
from jira.utils import build_agent_context, detect_operator, parse_jira_issue_key


# Map ask_agent errors to user-facing messages.
def _workflow_error_message(error: str | None) -> str:
    if error == "no_repo_writes":
        return (
            "agent concluded OUTCOME: implement but did not write any repo files "
            "(write_repo_file was not called successfully)"
        )
    return error or "unknown error"


def _print_workflow_result(
    result,
    *,
    repo_path: str,
    jira_branch: str | None = None,
    github_head_branch: str | None = None,
) -> None:
    print(result.response)
    if parse_workflow_outcome(result.response or "") == "no_code_change":
        print("\n--- No repo changes (OUTCOME: no_code_change) ---")
        return
    print("\n--- Next steps (operator repo; not run automatically) ---")
    print(f"  cd {repo_path}")
    if jira_branch:
        print(f"  git fetch origin && git checkout -B {jira_branch}")
        print("  git status && git add ... && git commit && git push -u origin HEAD && gh pr create --fill")
    elif github_head_branch:
        print(f"  git fetch origin && git checkout {github_head_branch}")
        print("  git status && git add ... && git commit && git push")


# Suggest a feature branch name for a Jira-driven PR.
def _jira_branch_name(issue_key: str, summary: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", (summary or "").lower()).strip("-")[:40]
    return f"jira/{issue_key}" + (f"-{slug}" if slug else "")


# Phase 1: Jira URL or key → Vertex.
def _run_jira(target: str, *, prompt_only: bool) -> int:
    issue_key = parse_jira_issue_key(target)
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
    branch = _jira_branch_name(issue_key, context.get("title") or "")

    if prompt_only:
        print(build_prompt(
            context,
            AgentMode.PR_WORKFLOW_JIRA,
            operator=operator,
            op_name=op_name,
            repo_path=repo_path,
            branch_name=branch,
        ))
        return 0

    result = ask_agent(
        context,
        mode=AgentMode.PR_WORKFLOW_JIRA,
        repo_path=repo_path,
        operator=operator,
        op_name=op_name,
        branch_name=branch,
    )
    if not result.ok:
        print(f"pr-workflow: {_workflow_error_message(result.error)}", file=sys.stderr)
        return 1

    _print_workflow_result(result, repo_path=repo_path, jira_branch=branch)
    return 0


# Phase 2: GitHub PR URL → unresolved threads + diff → Vertex.
def _run_github_pr(target: str, *, prompt_only: bool) -> int:
    parsed = parse_github_pr_url(target)
    if not parsed:
        print("pr-workflow: not a GitHub pull request URL", file=sys.stderr)
        return 1
    owner, repo, pr_num = parsed
    gh_repo = f"{owner}/{repo}"

    matched = find_operator_for_github_repo(gh_repo, OPERATORS)
    if not matched:
        print(
            f"pr-workflow: no OPERATOR_* entry matches {gh_repo} "
            "(check OPERATOR_*_COMPONENTS vs repo name or origin URL)",
            file=sys.stderr,
        )
        return 1
    operator, repo_path, op_name = matched

    try:
        review = fetch_for_review(gh_repo, pr_num)
        unresolved = fetch_unresolved_threads(owner, repo, pr_num)
    except RuntimeError as e:
        print(f"pr-workflow: {e}", file=sys.stderr)
        return 1

    if not unresolved.strip():
        print("pr-workflow: no unresolved review threads; nothing to do.")
        return 0

    context = {
        "pr_url": review["url"],
        "title": review["title"],
        "body": review["body"],
        "base_branch": review["base_branch"],
        "head_branch": review["head_branch"],
        "unresolved_comments": unresolved,
        "diff": review["diff"],
    }

    if prompt_only:
        print(build_prompt(
            context,
            AgentMode.PR_WORKFLOW_GITHUB,
            operator=operator,
            op_name=op_name,
            repo_path=repo_path,
            base_branch=review["base_branch"],
            branch_name=review["head_branch"],
        ))
        return 0

    result = ask_agent(
        context,
        mode=AgentMode.PR_WORKFLOW_GITHUB,
        repo_path=repo_path,
        operator=operator,
        op_name=op_name,
        base_branch=review["base_branch"],
        branch_name=review["head_branch"],
    )
    if not result.ok:
        print(f"pr-workflow: {_workflow_error_message(result.error)}", file=sys.stderr)
        return 1

    _print_workflow_result(
        result, repo_path=repo_path, github_head_branch=review["head_branch"],
    )
    return 0


# Route target URL to Jira or GitHub workflow.
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PR workflow: Jira or GitHub PR URL")
    parser.add_argument("target", help="Jira URL/key or https://github.com/.../pull/N")
    parser.add_argument("-p", "--prompt", action="store_true", help="Print prompt only")
    args = parser.parse_args(argv)

    if parse_github_pr_url(args.target):
        return _run_github_pr(args.target, prompt_only=args.prompt)
    return _run_jira(args.target, prompt_only=args.prompt)


if __name__ == "__main__":
    sys.exit(main())
