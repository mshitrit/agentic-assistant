import json
import requests
from config.settings import JIRA_USER, JIRA_TOKEN, CLOUD_ID, AI_PREFIX, DEBUG_MODE, DebugMode
from jira.utils import extract_adf_text


def extract_comment_text(comment: dict) -> str:
    return extract_adf_text(comment.get("body", {}))


def has_ai_comment(fields: dict) -> bool:
    comments = fields.get("comment", {}).get("comments", [])
    return any(AI_PREFIX in extract_comment_text(c) for c in comments)


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
