"""CLI: run PR/MR code review via Vertex AI (prompt on stdin, review on stdout)."""

from __future__ import annotations

import os
import sys

from agent.vertex import complete_single_turn
from config.settings import PR_REVIEW_MAX_TOKENS, PR_REVIEW_MODEL


def main() -> int:
    prompt = sys.stdin.read()
    if not prompt.strip():
        print("pr-review: empty prompt on stdin", file=sys.stderr)
        return 1

    try:
        import anthropic  # noqa: F401
    except ImportError:
        print(
            'pr-review: missing anthropic; run: pip install "anthropic[vertex]"',
            file=sys.stderr,
        )
        return 1

    model = os.environ.get("PR_REVIEW_MODEL", PR_REVIEW_MODEL)
    max_tokens = int(os.environ.get("PR_REVIEW_MAX_TOKENS", str(PR_REVIEW_MAX_TOKENS)))

    result = complete_single_turn(prompt, max_tokens=max_tokens, model=model)
    if not result.ok:
        print(f"pr-review: {result.error}", file=sys.stderr)
        return 1

    print(result.response)
    return 0


if __name__ == "__main__":
    sys.exit(main())
