import time
from datetime import datetime
from config.settings import ISSUE_KEY, OPERATORS, POLL_INTERVAL, TRIGGER_LABEL, TRIGGER_COMMENT, LOG_LEVEL
from jira.client import fetch_issues_by_components, get_issue_details
from jira.comments import has_ai_comment, post_comment, extract_comment_text, post_restricted_issue_skip_notice
from jira.utils import extract_adf_text, detect_operator
from agent.claude import ask_agent
from telemetry.metrics import jira_metrics


def should_trigger(fields: dict) -> bool:
    has_label = TRIGGER_LABEL in fields.get("labels", [])
    comments = fields.get("comment", {}).get("comments", [])
    has_trigger_comment = any(TRIGGER_COMMENT in extract_comment_text(c) for c in comments)
    return has_label or has_trigger_comment


def _format_comments(comments: list) -> str:
    lines = []
    for i, c in enumerate(comments, 1):
        author = (c.get("author") or {}).get("displayName", "Unknown")
        text = extract_comment_text(c).strip()
        if text:
            lines.append(f"Comment {i} ({author}): {text}")
    return "\n".join(lines)


if __name__ == "__main__":
    if ISSUE_KEY:
        issue_keys = [ISSUE_KEY]
        print(f"Tracking specific ticket: {ISSUE_KEY}")
    else:
        all_components = [c for op in OPERATORS.values() for c in op.get("components", [])]
        issue_keys = fetch_issues_by_components(all_components)
        print(f"Tracking {len(issue_keys)} tickets from operators: {list(OPERATORS.keys())}")

    print(f"Polling every {POLL_INTERVAL}s...")

    while True:
        time.sleep(POLL_INTERVAL)
        print(f"\n--- Poll cycle {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
        for key in issue_keys:
            fields = get_issue_details(key)
            if fields is None:
                continue
            if not should_trigger(fields):
                if LOG_LEVEL == "DEBUG":
                    print(f"No trigger on {key}, skipping.")
                continue
            if has_ai_comment(fields):
                if LOG_LEVEL == "DEBUG":
                    print(f"AI comment already exists on {key}, skipping.")
                continue
            if fields.get("security") is not None:
                print(
                    f"[INFO] {key} has a Jira security level; skipping external AI, posting explanation comment."
                )
                post_restricted_issue_skip_notice(key)
                continue
            title = fields["summary"]
            print(f"Trigger detected on {key}: '{title}'")
            public_comments = fields.get("comment", {}).get("public_comments", [])
            context = {
                "title":       fields.get("summary"),
                "description": extract_adf_text(fields.get("description") or {}),
                "status":      fields.get("status", {}).get("name"),
                "priority":    fields.get("priority", {}).get("name"),
                "issue_type":  fields.get("issuetype", {}).get("name"),
                "assignee":    (fields.get("assignee") or {}).get("displayName"),
                "components":  [c["name"] for c in fields.get("components", [])],
                "comments":    _format_comments(public_comments),
            }
            operator = detect_operator(fields, OPERATORS)
            if operator is None:
                print(f"[WARNING] No operator matched for {key}, skipping analysis.")
                continue
            op_name   = OPERATORS[operator]["components"][0]
            repo_path = OPERATORS[operator].get("repo_path", "")
            agent_result = ask_agent(context, operator=operator, op_name=op_name, repo_path=repo_path)
            if not agent_result.ok:
                jira_metrics.inc_errors()
                print(f"[ERROR] Agent failed on {key}: {agent_result.error}, skipping comment.")
                continue
            print(f"Agent response: {agent_result.response}")
            labeled_response = f"*Analyzed as: {op_name}*\n\n{agent_result.response}"
            post_comment(key, labeled_response)
            jira_metrics.inc_analyses_posted()
        print("--- End of cycle ---")
        jira_metrics._print()
