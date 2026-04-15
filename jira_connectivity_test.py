import requests
import json

# ==========================================
# 1. Configuration (Fill these in!)
# ==========================================
JIRA_DOMAIN = "https://redhat.atlassian.net"

config = {}
with open("jira_config.txt") as f:
    for line in f:
        key, _, value = line.strip().partition("=")
        config[key] = value

JIRA_USER  = config["JIRA_USER"]
# Jira Cloud (redhat.atlassian.net): use your Atlassian account email + API Token
# API tokens: https://id.atlassian.com/manage-profile/security/api-tokens
JIRA_TOKEN = config["JIRA_TOKEN"]
ISSUE_KEY  = config["ISSUE_KEY"]

# ==========================================
# 2. Setup the Request
# ==========================================
url = f"{JIRA_DOMAIN}/rest/api/2/issue/{ISSUE_KEY}/comment"

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# The message you want to post
payload = json.dumps({
    "body": "🤖 **ACK:** Hello from Python! Verifying write access to this ticket."
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
