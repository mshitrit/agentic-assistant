from fastapi import FastAPI, Request
import requests
from requests.auth import HTTPBasicAuth

app = FastAPI()

# Your Jira credentials
JIRA_DOMAIN = "https://your-company.atlassian.net"
JIRA_EMAIL = "your-service-account@redhat.com"
JIRA_API_TOKEN = "your_generated_api_token"

@app.post("/jira-webhook")
async def handle_jira_webhook(request: Request):
    # 1. Receive the payload from Jira
    payload = await request.json()
    
    # 2. Extract the ticket key (e.g., "ENG-404")
    issue_key = payload.get("issue", {}).get("key")
    
    if not issue_key:
        return {"message": "No issue key found, ignoring."}

    # 3. Formulate the ACK comment
    comment_url = f"{JIRA_DOMAIN}/rest/api/2/issue/{issue_key}/comment"
    auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {"Content-Type": "application/json"}
    payload = {
        "body": "🤖 **ACK:** The automation pipeline has successfully received this ticket. AI analysis capabilities coming soon!"
    }

    # 4. Post the comment back to Jira
    response = requests.post(comment_url, json=payload, headers=headers, auth=auth)

    if response.status_code == 201:
        return {"message": f"Successfully ACK'd {issue_key}"}
    else:
        return {"message": f"Failed to ACK. Jira returned: {response.status_code}"}
