from fastapi import FastAPI, Request
import requests
import json

app = FastAPI()

# Load credentials and config from jira_config.txt
config = {}
with open("jira_config.txt") as f:
    for line in f:
        key, _, value = line.strip().partition("=")
        config[key] = value

JIRA_USER  = config["JIRA_USER"]
JIRA_TOKEN = config["JIRA_TOKEN"]
CLOUD_ID   = config["CLOUD_ID"]
ISSUE_KEY  = config["ISSUE_KEY"]

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/jira-webhook")
async def handle_jira_webhook(request: Request):
    # 1. Receive the payload from Jira
    payload = await request.json()

    # 2. Extract the ticket key (e.g., "RHWA-904")
    issue_key = payload.get("issue", {}).get("key")

    if not issue_key:
        return {"message": "No issue key found, ignoring."}

    # 3. Only process the tracked ticket
    if issue_key != ISSUE_KEY:
        return {"message": f"Not tracking {issue_key}, ignoring."}

    # 4. Only react to status change events
    changelog = payload.get("changelog", {})
    status_changed = any(
        item.get("field") == "status"
        for item in changelog.get("items", [])
    )

    if not status_changed:
        return {"message": "Not a status change, ignoring."}

    # 5. Post a comment back to the ticket (API v3 with ADF payload)
    comment_url = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/issue/{issue_key}/comment"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
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
                            "text": "ACK: Status change detected. The automation pipeline has been notified."
                        }
                    ]
                }
            ]
        }
    })

    response = requests.post(
        comment_url,
        data=body,
        headers=headers,
        auth=(JIRA_USER, JIRA_TOKEN),
        timeout=10
    )

    if response.status_code == 201:
        return {"message": f"Successfully posted comment on {issue_key}"}
    else:
        return {"message": f"Failed to post comment. Jira returned: {response.status_code}", "details": response.text}


def register_webhook(listener_url: str):
    url = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/webhook"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    body = {
        "url": listener_url,
        "webhooks": [
            {
                "events": ["jira:issue_updated"],
                "jqlFilter": f"issue = {ISSUE_KEY}"
            }
        ]
    }
    response = requests.post(url, json=body, headers=headers, auth=(JIRA_USER, JIRA_TOKEN), timeout=10)
    if response.status_code == 200:
        print(f"Webhook registered successfully for {ISSUE_KEY}.")
    else:
        print(f"Failed to register webhook: {response.status_code} - {response.text}")
