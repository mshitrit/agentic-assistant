# Agentic Assistant

A Python-based PoC that monitors a Jira ticket for status changes and triggers a Claude AI agent to post a contextual comment in response.

## Scripts

| File | Description |
|---|---|
| `jira_connectivity_test.py` | One-shot test to verify Jira credentials and write access |
| `status_poller.py` | Polls a Jira ticket every 20s, detects status changes, and posts an AI-generated comment |

## Prerequisites

### 1. Python
Required to run any script in this project.
```bash
sudo dnf install python3
```

### 2. Jira client library
Required by both scripts to make HTTP calls to the Jira REST API.
```bash
pip install requests
```

### 3. Claude AI library (for `status_poller.py` only)
Required to call the Claude AI model via Google Cloud Vertex AI.
```bash
pip install "anthropic[vertex]"
```

### 4. Google Cloud CLI (for `status_poller.py` only)
Required to authenticate with GCP so the Claude library can access Vertex AI.

Install:
```bash
sudo dnf install google-cloud-cli
```

Authenticate (one-time):
```bash
gcloud auth application-default login
```

> Also ensure Claude is enabled in your GCP project's [Vertex AI Model Garden](https://console.cloud.google.com/vertex-ai/model-garden)

## Configuration

Copy the template and fill in your values:
```bash
cp jira_config.template.txt jira_config.txt
```

See `jira_config.template.txt` for field descriptions and how to retrieve each value.

> `jira_config.txt` is git-ignored and should never be committed.

## Usage

**Test Jira connectivity first:**
```bash
python jira_connectivity_test.py
```

**Start the status poller:**
```bash
python status_poller.py
```
