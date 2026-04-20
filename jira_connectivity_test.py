import json
import requests
from config.settings import JIRA_USER, JIRA_TOKEN, CLOUD_ID, ISSUE_KEY

# Connectivity test script for Jira Cloud.
# Verifies that authentication and write access are working correctly by posting
# a test comment to the configured issue (ISSUE_KEY in jira_config.txt).
# Run once to confirm credentials before using poller.py.

# ==========================================
# Setup the Request
# ==========================================
url = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/issue/{ISSUE_KEY}/comment"

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# The message you want to post (API v3 requires Atlassian Document Format)
payload = json.dumps({
    "body": {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "ACK: Hello from Python! Verifying write access to this ticket."
                    }
                ]
            }
        ]
    }
})

# ==========================================
# Execute and Verify
# ==========================================
print(f"Attempting to post comment to {ISSUE_KEY}...")

response = requests.post(
    url,
    data=payload,
    headers=headers,
    auth=(JIRA_USER, JIRA_TOKEN),
    timeout=10
)

if response.status_code == 201:
    print("✅ Success! Check your Jira ticket to see the comment.")
else:
    print(f"❌ Failed. Jira returned status code: {response.status_code}")
    print("Response details:", response.text)
