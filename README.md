# Agentic Assistant

A Python-based PoC that monitors Jira tickets and triggers a Claude AI agent to post a contextual comment when requested via a label or comment.

## Project Structure

```
agentic-assistant/
├── config/
│   ├── settings.py               # loads config/config.txt, exposes all constants
│   └── config.template.txt       # configuration template
├── jira/
│   ├── client.py                 # fetch issues and issue details from Jira API
│   └── comments.py               # post, check and parse Jira comments
├── agent/
│   └── claude.py                 # Claude AI via Vertex AI
├── docs/                         # reference documentation
│   ├── SLACK_BOT_SETUP.md        # Slack app setup guide
│   ├── ROADMAP.md                # future enhancements
│   └── TECH_DEBT.md              # known technical debt
├── scripts/
│   ├── agentic-assist-menu.sh     # interactive menu for user scripts
│   ├── internal/
│   │   └── update-operator-repos.sh  # git pull for each OPERATOR_*_REPO_PATH (deploy/cron)
│   ├── user/                      # user-triggered scripts (also via menu)
│   │   ├── jira-assist.sh         # one-shot Jira analysis to console only
│   │   ├── pr-workflow.sh         # Jira URL or GitHub PR URL → Vertex + operator repo writes
│   │   ├── pr-review.sh           # PR/MR review via gh/glab
│   │   ├── sync-living-from-remote.sh
│   │   └── reset-living-from-verified.sh
│   └── lib/
│       ├── find_python.sh         # find_python() — source from scripts that need it
│       └── menu.sh                # prompts for agentic-assist-menu.sh
├── plans/                        # implementation plans (deleted after completion)
├── main.py                       # Jira poller entry point
├── slack_bot_main.py             # Slack bot entry point
├── deploy.sh                     # deployment script (git sync, memory seed, operator sync, cron, restart)
└── jira_connectivity_test.py     # one-shot connectivity and write access test
```

## Scripts

| File | Description |
|---|---|
| `jira_connectivity_test.py` | One-shot test to verify Jira credentials and write access |
| `main.py` | Polls tracked Jira tickets on an interval (default 60s via `POLL_INTERVAL` in `config/settings.py`) and posts an AI-generated comment when an `ai-assist` label or `/ai-assist` comment is detected |
| `slack_bot_main.py` | Listens for `@mentions` in Slack and responds with AI-generated answers using the same domain knowledge as the Jira agent (see [Slack Bot Setup](docs/SLACK_BOT_SETUP.md)) |
| `deploy.sh` | Reads `DEPLOY_GIT_BRANCH` from `config/config.txt` (default `main`), `fetch` + hard reset to `origin/<branch>`, seeds empty `memory/living/` from verified memory, runs `scripts/internal/update-operator-repos.sh`, installs a daily 02:00 cron job for operator repo sync (`AGENTIC_CRON_JOB=operator_repo_sync`), restarts selected processes, then `tail -f` on the new log files |
| `scripts/internal/update-operator-repos.sh` | For each `OPERATOR_*_REPO_PATH` in `config/config.txt`, runs `git pull origin main`; append-only log at `logs/operator-repos-sync.log` |
| `scripts/agentic-assist-menu.sh` | Interactive menu for user scripts (implement, review, Jira analysis, memory, setup). |
| `scripts/user/jira-assist.sh` | One-shot Jira URL/key analysis to stdout only (no Jira comments, labels, or ticket updates). |
| `scripts/user/pr-workflow.sh` | Jira URL/key or GitHub `.../pull/N` → Vertex; uses `github/pr.py` (same PR fetch as `pr-review.sh`) plus unresolved review threads. Optional `-c` / `-f` / `PR_WORKFLOW_CONTEXT_FILE` for extra prompt instructions. Requires `gh`. No auto-commit/PR. |
| `scripts/user/pr-review.sh` | Review a GitHub PR or GitLab MR from its URL via `gh` / `glab`. |
| `scripts/user/sync-living-from-remote.sh` | Rsync `memory/living/` from another host into this repo's `memory/verified/` (for diff review in the IDE). Defaults: `REMOTE=root@bkr1.local`, `REMOTE_ROOT=/root/gitrepos/agentic-assistant`. Override with env vars. |
| `scripts/user/reset-living-from-verified.sh` | Overwrites `memory/living/` with `memory/verified/` using `rsync --delete` — use after you have merged updates into verified and want the agent scratch tree to match (e.g. before the next deploy or poller run). |

## Prerequisites

### 1. Python 3.10+
Required to run any script in this project. Python 3.10 or newer is required (uses `X | Y` union type syntax).

Check your version:
```bash
python3 --version
```

If below 3.10, install a newer version (RHEL/Fedora):
```bash
sudo dnf install python3.11
```
Then use `python3.11` instead of `python3` for all commands below and when running the project.

### 2. Jira client library
Required by both scripts to make HTTP calls to the Jira REST API.
```bash
pip install requests
```

### 3. Claude AI library (for `main.py` and `slack/slack_bot.py`)
Required to call the Claude AI model via Google Cloud Vertex AI.
```bash
pip install "anthropic[vertex]"
```

### 4. Google Cloud CLI (for `main.py` and `slack/slack_bot.py`)
Required to authenticate with GCP so the Claude library can access Vertex AI.

Add the Google Cloud repo (required — not in default Fedora/RHEL repos):
```bash
sudo tee -a /etc/yum.repos.d/google-cloud-sdk.repo << EOM
[google-cloud-cli]
name=Google Cloud CLI
baseurl=https://packages.cloud.google.com/yum/repos/cloud-sdk-el10-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=0
gpgkey=https://packages.cloud.google.com/yum/doc/rpm-package-key-v10.gpg
EOM
```

Install:
```bash
sudo dnf install google-cloud-cli
```

Authenticate (one-time):
```bash
gcloud init --console-only
```
When prompted, enter your GCP project ID (`GCP_PROJECT_ID` from your config).

Then set the quota project:
```bash
gcloud auth application-default set-quota-project <GCP_PROJECT_ID>
```

Verify authentication:
```bash
gcloud auth list
```

> Also ensure Claude is enabled in your GCP project's [Vertex AI Model Garden](https://console.cloud.google.com/vertex-ai/model-garden)

### 5. Slack bot library (for `slack_bot_main.py` only)
Required to connect to Slack via Socket Mode.
```bash
python3.11 -m pip install slack_bolt
```

## Configuration

Copy the template and fill in your values:
```bash
cp config/config.template.txt config/config.txt
```

See `config/config.template.txt` for field descriptions and how to retrieve each value.

> `config/config.txt` is git-ignored and should never be committed.

## Memory

The agent uses a two-tier memory system to provide domain-aware analysis:

### Operator Keys

Each operator is identified by a short key (e.g. `sbr`, `far`) defined in `config/config.txt` via `OPERATOR_{KEY}_*` entries. The key is load-bearing — it must be consistent across three places:
- **Memory directories:** `memory/verified/{key}/` and `memory/living/{key}/`
- **Slack tag:** users prefix questions with `[KEY]` (e.g. `[SBR] how does fencing work?`)
- **Config entries:** `OPERATOR_{KEY}_COMPONENTS` and `OPERATOR_{KEY}_REPO_PATH`

Use short, uppercase keys in config (e.g. `SBR`, `FAR`) — they are lowercased internally.

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

### Syncing living memory from a remote host

To copy another machine's `memory/living/` into **this** clone's `memory/verified/` (so Git and the IDE show diffs against your branch), run `./scripts/user/sync-living-from-remote.sh`. It uses `rsync` over SSH and does **not** pass `--delete`, so files that exist only under local `memory/verified/` are left unchanged. Set `REMOTE` and/or `REMOTE_ROOT` if your host or path differ; the script prints the resolved values and, when both defaults are used, how to override them.

### Resetting living from verified

After you have resolved diffs and updated `memory/verified/`, run `./scripts/user/reset-living-from-verified.sh` to replace `memory/living/` with a mirror of verified (`rsync` with `--delete`, so extra files only under living are removed). Useful before restarting the poller or Slack bot so the agent starts from the same baseline as git-tracked memory.

## How to Request AI Analysis

The agent can be triggered on any tracked Jira ticket using either method:

### Option 1: Add a label
Add the label `ai-assist` to the ticket via the Jira UI.

### Option 2: Post a comment
Add a comment containing `/ai-assist` anywhere in the text.

Once triggered, the agent will post an AI-generated comment (prefixed with 🤖 [AI Generated]) on the ticket.
The agent will only comment once per trigger — if an AI-generated comment already exists, it will not post again.
To request another analysis, remove the existing AI comment or add a new `/ai-assist` comment.

### Option 3: One-shot shell trigger (console output only)
Run AI analysis for a Jira issue from shell, without writing anything back to Jira:

```bash
./scripts/user/jira-assist.sh RHWA-1017
# or
./scripts/user/jira-assist.sh https://redhat.atlassian.net/browse/RHWA-1017
```

This command prints the AI output to stdout and does not post comments or update ticket fields.
Use `--internal` to include internal comments in prompt context.

### Interactive menu
For most user workflows, run the interactive menu from repo root:

```bash
./scripts/agentic-assist-menu.sh
```

It covers implementation workflow, PR review, Jira analysis, memory management, and one-time setup (auth / CLI install).
Individual scripts under `scripts/user/` can still be invoked directly.

## Deployment

From the repo root, run `./deploy.sh jira`, `./deploy.sh slack`, or `./deploy.sh both`. The script aligns this repository to `origin/<DEPLOY_GIT_BRANCH>` (see `config/config.txt`; discards local git changes on tracked files), ensures living memory exists, syncs configured operator code clones once, refreshes the crontab entry for a daily 02:00 operator-repo pull (if `crontab` is available), stops any running poller/bot for this tree, starts the chosen processes under `nohup` with timestamped logs under `logs/`, then follows those logs. Operator sync output is also written to `logs/operator-repos-sync.log`.

## Usage

**Test Jira connectivity first:**
```bash
python jira_connectivity_test.py
```

**Start the poller:**
```bash
python main.py
```

**Start the Slack bot:**
```bash
python3.11 slack_bot_main.py
```
Then mention the bot in your Slack channel: `@sbr-assistant how does detectOnlyMode work?`
