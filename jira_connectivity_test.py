import requests
import json

# ==========================================
# 1. Configuration (Fill these in!)
# ==========================================
JIRA_DOMAIN = "https://issues.redhat.com"  # Update if using a different instance
ISSUE_KEY = "PROJ-123"                     # The specific ticket to test on

# Authentication details
# If using a Service Account or standard Jira Cloud, use Username + API Token.
# If Red Hat's internal Jira requires a Personal Access Token (PAT), see the note below.
JIRA_USER = "your-email@redhat.com"
JIRA_TOKEN = "your_api_or_personal_access_token"

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
    auth=(JIRA_USER, JIRA_TOKEN)
)

# Check the results
if response.status_code == 201:
    print("✅ Success! Check your Jira ticket to see the comment.")
else:
    print(f"❌ Failed. Jira returned status code: {response.status_code}")
    print("Response details:", response.text)
