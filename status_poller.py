import requests
import json
import time

config = {}
with open("jira_config.txt") as f:
    for line in f:
        key, _, value = line.strip().partition("=")
        config[key] = value

JIRA_USER  = config["JIRA_USER"]
JIRA_TOKEN = config["JIRA_TOKEN"]
CLOUD_ID   = config["CLOUD_ID"]
ISSUE_KEY  = config["ISSUE_KEY"]

POLL_INTERVAL = 20  # seconds


def get_issue_status():
    url = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/issue/{ISSUE_KEY}"
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers, auth=(JIRA_USER, JIRA_TOKEN), timeout=10)
    response.raise_for_status()
    return response.json()["fields"]["status"]["name"]


def post_comment(old_status: str, new_status: str):
    url = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/issue/{ISSUE_KEY}/comment"
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
                            "text": f"ACK: Status changed from '{old_status}' to '{new_status}'."
                        }
                    ]
                }
            ]
        }
    })
    response = requests.post(url, data=body, headers=headers, auth=(JIRA_USER, JIRA_TOKEN), timeout=10)
    if response.status_code == 201:
        print(f"Comment posted: {old_status} → {new_status}")
    else:
        print(f"Failed to post comment: {response.status_code} - {response.text}")


if __name__ == "__main__":
    print(f"Polling {ISSUE_KEY} every {POLL_INTERVAL}s...")
    last_status = get_issue_status()
    print(f"Initial status: {last_status}")

    while True:
        time.sleep(POLL_INTERVAL)
        current_status = get_issue_status()
        if current_status != last_status:
            print(f"Status changed: {last_status} → {current_status}")
            post_comment(last_status, current_status)
            last_status = current_status
        else:
            print(f"No change. Status: {current_status}")
