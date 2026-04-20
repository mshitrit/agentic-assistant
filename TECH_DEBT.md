# Technical Debt

## 1. Replace Polling with Jira Webhook

**Current approach:** `main.py` polls Jira every 20 seconds to check for trigger conditions.

**Why polling was chosen:** Webhook registration requires Jira admin permissions, which were not available. Polling was used as a simpler alternative sufficient for PoC purposes.

**Why this is debt:**
- Inefficient — makes API calls every cycle regardless of activity
- Reaction time bounded by poll interval (currently 20s)
- Higher API usage, potential rate limiting at scale

## 2. Designated Jira Account for the AI Agent

**Current approach:** The agent posts comments using a personal user account (configured via `JIRA_USER`/`JIRA_TOKEN`).

**Why this is debt:**
- Comments appear as coming from a real user, making it hard to distinguish AI-generated activity from human activity at a glance
- Ties the agent to a specific person's credentials

**Desired solution:** Create a dedicated Jira service account for the agent (e.g. `ai-agent@redhat.com`). This makes AI activity clearly identifiable in the audit trail and decouples the agent from any individual's account.
