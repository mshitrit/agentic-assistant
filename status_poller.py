import requests
import json
import time
import anthropic
from enum import Flag, auto

# Polls Jira issues every 20 seconds and checks for opt-in AI assist triggers.
# Watches either a specific ticket (ISSUE_KEY) or all open tickets belonging
# to the configured components (COMPONENTS). When a ticket has the "ai-assist"
# label or a comment containing "/ai-assist", the agent posts an AI-generated comment.

config = {}
with open("jira_config.txt") as f:
    for line in f:
        key, _, value = line.strip().partition("=")
        config[key] = value

JIRA_USER   = config["JIRA_USER"]
JIRA_TOKEN  = config["JIRA_TOKEN"]
CLOUD_ID    = config["CLOUD_ID"]
ISSUE_KEY   = config.get("ISSUE_KEY", "").strip()
COMPONENTS  = [c.strip() for c in config.get("COMPONENTS", "").split(",") if c.strip()]
GCP_PROJECT = config["GCP_PROJECT_ID"]
GCP_REGION  = config["GCP_REGION"]

POLL_INTERVAL   = 20          # seconds
AI_PREFIX       = "🤖 [AI Generated]\n\n"
TRIGGER_LABEL   = "ai-assist"
TRIGGER_COMMENT = "/ai-assist"


class DebugMode(Flag):
    PRODUCTION   = 0
    DISABLE_JIRA = auto()  # print comments to console instead of posting to Jira
    DISABLE_AI   = auto()  # skip Claude call, use a hardcoded response instead
    FULL_DISABLE = DISABLE_JIRA | DISABLE_AI

DEBUG_MODE = DebugMode[config.get("DEBUG_MODE", "PRODUCTION")]


def fetch_issues_by_components(components: list[str]) -> list[str]:
    jql = "component in ({}) AND statusCategory != Done".format(
        ", ".join(f'"{c}"' for c in components)
    )
    url = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/search/jql"
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers, params={"jql": jql, "fields": "key"}, auth=(JIRA_USER, JIRA_TOKEN), timeout=10)
    response.raise_for_status()
    return [issue["key"] for issue in response.json().get("issues", [])]


def extract_comment_text(comment: dict) -> str:
    paragraphs = comment.get("body", {}).get("content", [])
    return " ".join(
        item.get("text", "")
        for para in paragraphs
        for item in para.get("content", [])
        if item.get("type") == "text"
    )


def get_issue_details(issue_key: str) -> dict:
    url = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/issue/{issue_key}"
    headers = {"Accept": "application/json"}
    params = {"fields": "summary,labels,comment"}
    response = requests.get(url, headers=headers, params=params, auth=(JIRA_USER, JIRA_TOKEN), timeout=10)
    response.raise_for_status()
    return response.json()["fields"]


def should_trigger(fields: dict) -> bool:
    has_label = TRIGGER_LABEL in fields.get("labels", [])
    comments = fields.get("comment", {}).get("comments", [])
    has_trigger_comment = any(TRIGGER_COMMENT in extract_comment_text(c) for c in comments)
    return has_label or has_trigger_comment


def has_ai_comment(fields: dict) -> bool:
    comments = fields.get("comment", {}).get("comments", [])
    return any(AI_PREFIX in extract_comment_text(c) for c in comments)


def ask_agent(title: str) -> str:
    if DebugMode.DISABLE_AI in DEBUG_MODE:
        return f"[DEBUG] AI disabled. Ticket '{title}' requested AI analysis."
    client = anthropic.AnthropicVertex(project_id=GCP_PROJECT, region=GCP_REGION)
    prompt = (
        f"A Jira ticket titled '{title}' has been flagged for AI analysis. "
        f"Briefly acknowledge this and suggest a next action in 1-2 sentences."
    )
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def post_comment(issue_key: str, agent_response: str):
    if DebugMode.DISABLE_JIRA in DEBUG_MODE:
        print(f"[DEBUG] Would post comment on {issue_key}: {agent_response}")
        return
    full_comment = AI_PREFIX + agent_response
    url = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/issue/{issue_key}/comment"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    body = json.dumps({
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": full_comment
                        }
                    ]
                }
            ]
        }
    })
    response = requests.post(url, data=body, headers=headers, auth=(JIRA_USER, JIRA_TOKEN), timeout=10)
    if response.status_code == 201:
        print(f"Comment posted successfully on {issue_key}.")
    else:
        print(f"Failed to post comment on {issue_key}: {response.status_code} - {response.text}")


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
