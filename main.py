import time
from datetime import datetime
from config.settings import ISSUE_KEY, COMPONENTS, POLL_INTERVAL, TRIGGER_LABEL, TRIGGER_COMMENT
from jira.client import fetch_issues_by_components, get_issue_details
from jira.comments import has_ai_comment, post_comment, extract_comment_text
from agent.claude import ask_agent


def should_trigger(fields: dict) -> bool:
    has_label = TRIGGER_LABEL in fields.get("labels", [])
    comments = fields.get("comment", {}).get("comments", [])
    has_trigger_comment = any(TRIGGER_COMMENT in extract_comment_text(c) for c in comments)
    return has_label or has_trigger_comment


if __name__ == "__main__":
    if ISSUE_KEY:
        issue_keys = [ISSUE_KEY]
        print(f"Tracking specific ticket: {ISSUE_KEY}")
    else:
        issue_keys = fetch_issues_by_components(COMPONENTS)
        print(f"Tracking {len(issue_keys)} tickets from components: {COMPONENTS}")

    print(f"Polling every {POLL_INTERVAL}s...")

    while True:
        time.sleep(POLL_INTERVAL)
        print(f"\n--- Poll cycle {datetime.now().strftime('%H:%M:%S')} ---")
        for key in issue_keys:
            fields = get_issue_details(key)
            if not should_trigger(fields):
                print(f"No trigger on {key}, skipping.")
                continue
            if has_ai_comment(fields):
                print(f"AI comment already exists on {key}, skipping.")
                continue
            title = fields["summary"]
            print(f"Trigger detected on {key}: '{title}'")
            agent_response = ask_agent(title)
            print(f"Agent response: {agent_response}")
            post_comment(key, agent_response)
        print("--- End of cycle ---")
