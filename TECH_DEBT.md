# Technical Debt

## 1. Replace Polling with Jira Webhook

**Current approach:** `main.py` polls Jira every 20 seconds to check for trigger conditions.

**Why polling was chosen:** Webhook registration requires Jira admin permissions, which were not available. Polling was used as a simpler alternative sufficient for PoC purposes.

**Why this is debt:**
- Inefficient — makes API calls every cycle regardless of activity
- Reaction time bounded by poll interval (currently 20s)
- Higher API usage, potential rate limiting at scale

**Desired solution:** Register a Jira webhook pointing to a FastAPI listener, eliminating the polling loop entirely.
