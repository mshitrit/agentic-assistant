"""GitHub PR fetch via gh — shared by scripts/pr-review.sh and agent/pr_workflow.py."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_GITHUB_PR_URL = re.compile(
    r"^https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)/?(?:\?.*)?$",
    re.IGNORECASE,
)

_REVIEW_JSON_FIELDS = "title,body,baseRefName,headRefName,author,url,additions,deletions,changedFiles"

_GQL_THREADS = """
query ($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      reviewThreads(first: 100) {
        nodes {
          isResolved path line
          comments(first: 30) { nodes { body author { login } } }
        }
      }
    }
  }
}
"""


# Return (owner, repo, pr_number) from a github.com/pull/N URL, or None.
def parse_github_pr_url(url: str) -> tuple[str, str, int] | None:
    m = _GITHUB_PR_URL.match((url or "").strip())
    if not m:
        return None
    return m.group(1), m.group(2), int(m.group(3))


# Run gh with args; raise RuntimeError on failure.
def _run_gh(args: list[str], *, timeout: int = 120) -> str:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "gh command failed")
    return proc.stdout


# Fetch PR metadata and full diff (same data as pr-review.sh fetch_github).
def fetch_for_review(gh_repo: str, pr_num: int) -> dict[str, str]:
    meta_raw = _run_gh(
        ["pr", "view", str(pr_num), "-R", gh_repo, "--json", _REVIEW_JSON_FIELDS]
    )
    meta = json.loads(meta_raw)
    diff = _run_gh(["pr", "diff", str(pr_num), "-R", gh_repo], timeout=300)
    return {
        "meta_json": meta_raw,
        "diff": diff,
        "url": meta.get("url") or f"https://github.com/{gh_repo}/pull/{pr_num}",
        "title": meta.get("title") or "",
        "body": meta.get("body") or "",
        "base_branch": meta.get("baseRefName") or "",
        "head_branch": meta.get("headRefName") or "",
        "ref_label": f"{gh_repo} pull #{pr_num}",
    }


# Map a git origin URL to owner/repo for github.com remotes.
def _normalize_origin_to_slug(remote_url: str) -> str | None:
    u = remote_url.strip()
    if m := re.match(r"git@github\.com:([^/]+)/(.+?)(?:\.git)?$", u, re.I):
        return f"{m.group(1)}/{m.group(2)}"
    if m := re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", u, re.I):
        return f"{m.group(1)}/{m.group(2)}"
    return None


# Find operator key and local clone whose origin matches gh_repo.
def find_operator_for_github_repo(
    gh_repo: str,
    operators: dict[str, dict],
) -> tuple[str, str, str] | None:
    want = gh_repo.lower()
    for op_key, cfg in operators.items():
        rp = (cfg.get("repo_path") or "").strip()
        if not rp or not Path(rp).is_dir():
            continue
        proc = subprocess.run(
            ["git", "-C", rp, "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            continue
        slug = _normalize_origin_to_slug(proc.stdout)
        if slug and slug.lower() == want:
            comps = cfg.get("components") or []
            return op_key, rp, (comps[0] if comps else op_key)
    return None


# Turn GraphQL reviewThreads JSON into markdown for unresolved threads only.
def format_unresolved_threads(gql_payload: dict[str, Any]) -> str:
    nodes = (
        gql_payload.get("data", {})
        .get("repository", {})
        .get("pullRequest", {})
        .get("reviewThreads", {})
        .get("nodes")
        or []
    )
    lines: list[str] = []
    n = 0
    for t in nodes:
        if t.get("isResolved"):
            continue
        path = t.get("path") or "?"
        line = t.get("line")
        loc = f"{path}:{line}" if line is not None else path
        n += 1
        lines.append(f"### Thread {n} ({loc})")
        for c in (t.get("comments") or {}).get("nodes") or []:
            login = (c.get("author") or {}).get("login", "?")
            body = (c.get("body") or "").strip()
            if body:
                lines.append(f"- **@{login}:** {body}")
        lines.append("")
    return "\n".join(lines).strip()


# Fetch unresolved PR review threads via gh api graphql.
def fetch_unresolved_threads(owner: str, repo: str, pr_num: int) -> str:
    variables = json.dumps({"owner": owner, "name": repo, "number": pr_num})
    out = _run_gh(
        ["api", "graphql", "-f", f"query={_GQL_THREADS}", "-f", f"variables={variables}"]
    )
    return format_unresolved_threads(json.loads(out))


# CLI for pr-review.sh: review-fetch OWNER/REPO PR_NUM → JSON on stdout.
def main() -> int:
    if len(sys.argv) != 4 or sys.argv[1] != "review-fetch":
        print("usage: python -m github.pr review-fetch OWNER/REPO PR_NUM", file=sys.stderr)
        return 2
    gh_repo, pr_num_s = sys.argv[2], sys.argv[3]
    try:
        data = fetch_for_review(gh_repo, int(pr_num_s))
    except (RuntimeError, json.JSONDecodeError, ValueError) as e:
        print(f"github.pr: {e}", file=sys.stderr)
        return 1
    print(json.dumps(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
