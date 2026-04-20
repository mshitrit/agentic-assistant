# Agentic Assistant

A Python-based PoC that monitors Jira tickets and triggers a Claude AI agent to post a contextual comment when requested via a label or comment.

## Project Structure

```
agentic-assistant/
├── config/
│   ├── settings.py               # loads jira_config.txt, exposes all constants
│   └── jira_config.template.txt  # configuration template
├── jira/
│   ├── client.py                 # fetch issues and issue details from Jira API
│   └── comments.py               # post, check and parse Jira comments
├── agent/
│   └── claude.py                 # Claude AI via Vertex AI
├── main.py                       # main loop and trigger detection
└── jira_connectivity_test.py     # one-shot connectivity and write access test
```

## Scripts

| File | Description |
|---|---|
| `jira_connectivity_test.py` | One-shot test to verify Jira credentials and write access |
| `main.py` | Polls tracked Jira tickets every 20s and posts an AI-generated comment when an `ai-assist` label or `/ai-assist` comment is detected |

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

### 3. Claude AI library (for `poller.py` only)
Required to call the Claude AI model via Google Cloud Vertex AI.
```bash
pip install "anthropic[vertex]"
```

### 4. Google Cloud CLI (for `poller.py` only)
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
cp config/jira_config.template.txt jira_config.txt
```

See `config/jira_config.template.txt` for field descriptions and how to retrieve each value.

> `jira_config.txt` is git-ignored and should never be committed.

## Memory

The agent uses a two-tier memory system to provide domain-aware analysis:

### Verified Memory (`memory/verified/`)
Human-curated knowledge base committed to git. Contains per-operator subdirectories (e.g. `memory/verified/sbr/`) with files covering overview, architecture, failure modes, runbook, and code map.

This is the stable, approved baseline the agent always consults.

### Living Memory (`memory/living/`)
Agent-maintained copy of the verified memory. Git-ignored — not committed.

**Setup (one-time):** Copy verified memory to living memory before running the poller:
```bash
cp -r memory/verified/ memory/living/
```

The agent may update files in `memory/living/` during ticket analysis when it detects discrepancies with the current codebase. Periodically review the diff between the two and promote correct changes to verified memory:
```bash
diff -r memory/verified/ memory/living/
```

## How to Request AI Analysis

The agent can be triggered on any tracked Jira ticket using either method:

### Option 1: Add a label
Add the label `ai-assist` to the ticket via the Jira UI.

### Option 2: Post a comment
Add a comment containing `/ai-assist` anywhere in the text.

Once triggered, the agent will post an AI-generated comment (prefixed with 🤖 [AI Generated]) on the ticket.
The agent will only comment once per trigger — if an AI-generated comment already exists, it will not post again.
To request another analysis, remove the existing AI comment or add a new `/ai-assist` comment.

## Usage

**Test Jira connectivity first:**
```bash
python jira_connectivity_test.py
```

**Start the poller:**
```bash
python main.py
```
