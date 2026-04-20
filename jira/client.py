import requests
from config.settings import JIRA_USER, JIRA_TOKEN, CLOUD_ID


def fetch_issues_by_components(components: list[str]) -> list[str]:
    jql = "component in ({}) AND statusCategory != Done".format(
        ", ".join(f'"{c}"' for c in components)
    )
    url = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/search/jql"
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers, params={"jql": jql, "fields": "key"}, auth=(JIRA_USER, JIRA_TOKEN), timeout=10)
    response.raise_for_status()
    return [issue["key"] for issue in response.json().get("issues", [])]


def get_issue_details(issue_key: str) -> dict:
    url = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/issue/{issue_key}"
    headers = {"Accept": "application/json"}
    params = {"fields": "summary,labels,comment,description,status,priority,assignee,issuetype,components"}
    response = requests.get(url, headers=headers, params=params, auth=(JIRA_USER, JIRA_TOKEN), timeout=10)
    response.raise_for_status()
    return response.json()["fields"]
