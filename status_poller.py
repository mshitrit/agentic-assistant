import requests
import json
import time
import anthropic
from enum import Flag, auto

# Polls Jira issues every 20 seconds and detects status changes.
# Watches either a specific ticket (ISSUE_KEY) or all open tickets belonging
# to the configured components (COMPONENTS). When a status change is detected,
# sends the ticket title to a Claude AI agent and posts its response as a comment.

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

POLL_INTERVAL = 20  # seconds


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
    url = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/search"
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers, params={"jql": jql, "fields": "key"}, auth=(JIRA_USER, JIRA_TOKEN), timeout=10)
    response.raise_for_status()
    return [issue["key"] for issue in response.json().get("issues", [])]


def get_issue_details(issue_key: str):
    url = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/issue/{issue_key}"
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers, auth=(JIRA_USER, JIRA_TOKEN), timeout=10)
    response.raise_for_status()
    fields = response.json()["fields"]
    return fields["status"]["name"], fields["summary"]


def ask_agent(title: str, old_status: str, new_status: str) -> str:
    if DebugMode.DISABLE_AI in DEBUG_MODE:
        return f"[DEBUG] AI disabled. Ticket '{title}' changed: '{old_status}' → '{new_status}'."
    client = anthropic.AnthropicVertex(project_id=GCP_PROJECT, region=GCP_REGION)
    prompt = (
        f"A Jira ticket titled '{title}' just changed status from '{old_status}' to '{new_status}'. "
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
                            "text": agent_response
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

    # initialise last known status for each ticket
    last_statuses = {}
    for key in issue_keys:
        status, _ = get_issue_details(key)
        last_statuses[key] = status
        print(f"  {key}: {status}")

    print(f"\nPolling every {POLL_INTERVAL}s...")

    while True:
        time.sleep(POLL_INTERVAL)
        for key in issue_keys:
            current_status, title = get_issue_details(key)
            if current_status != last_statuses[key]:
                print(f"Status changed on {key}: {last_statuses[key]} → {current_status}")
                agent_response = ask_agent(title, last_statuses[key], current_status)
                print(f"Agent response: {agent_response}")
                post_comment(key, agent_response)
                last_statuses[key] = current_status
            else:
                print(f"No change on {key}. Status: {current_status}")
