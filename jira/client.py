import requests
from config.settings import JIRA_USER, JIRA_TOKEN, CLOUD_ID
from jira.utils import jira_request


def _is_public_comment(comment: dict) -> bool:
    return comment.get("visibility") is None


@jira_request
def fetch_issues_by_components(components: list[str]) -> list[str]:
    jql = (
        "component in ({}) AND statusCategory != Done AND level is EMPTY".format(
            ", ".join(f'"{c}"' for c in components)
        )
    )
    url = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/search/jql"
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers, params={"jql": jql, "fields": "key"}, auth=(JIRA_USER, JIRA_TOKEN), timeout=10)
    response.raise_for_status()
    return [issue["key"] for issue in response.json().get("issues", [])]


@jira_request
def get_issue_details(issue_key: str) -> dict:
    url = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/issue/{issue_key}"
    headers = {"Accept": "application/json"}
    params = {"fields": "summary,labels,comment,description,status,priority,assignee,issuetype,components"}
    response = requests.get(url, headers=headers, params=params, auth=(JIRA_USER, JIRA_TOKEN), timeout=10)
    response.raise_for_status()
    fields = response.json()["fields"]
    all_comments = fields.get("comment", {}).get("comments", [])
    fields["comment"]["comments"] = all_comments
    fields["comment"]["public_comments"] = [c for c in all_comments if _is_public_comment(c)]
    return fields
