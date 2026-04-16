import requests
import json

# ==========================================
# 1. Configuration (Fill these in!)
# ==========================================
config = {}
with open("jira_config.txt") as f:
    for line in f:
        key, _, value = line.strip().partition("=")
        config[key] = value

JIRA_USER  = config["JIRA_USER"]
# Jira Cloud (redhat.atlassian.net): use your Atlassian account email + API Token
# Generate API tokens: https://id.atlassian.com/manage-profile/security/api-tokens
JIRA_TOKEN = config["JIRA_TOKEN"]
ISSUE_KEY  = config["ISSUE_KEY"]
# CLOUD_ID: found at https://api.atlassian.com/oauth/token/accessible-resources (the "id" field)
CLOUD_ID   = config["CLOUD_ID"]

# ==========================================
# 2. Setup the Request
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
# 3. Execute and Verify
# ==========================================
print(f"Attempting to post comment to {ISSUE_KEY}...")

# Sending the POST request using Basic Authentication
response = requests.post(
    url,
    data=payload,
    headers=headers,
    auth=(JIRA_USER, JIRA_TOKEN),
    timeout=10
)

# Check the results
if response.status_code == 201:
    print("✅ Success! Check your Jira ticket to see the comment.")
else:
    print(f"❌ Failed. Jira returned status code: {response.status_code}")
    print("Response details:", response.text)
