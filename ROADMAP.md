# Roadmap

## 1. Proactive Analysis of Unanswered Tickets

**Summary:** Automatically scan for tickets that have gone unanswered beyond a configurable threshold and generate a private AI analysis for developer review before any public comment is posted.

**Motivation:** Currently the agent only acts when explicitly triggered (`ai-assist` label or `/ai-assist` comment). Many tickets could benefit from early analysis without requiring manual opt-in, particularly tickets with no engineer response after several days.

**Trigger condition (suggested):**
- Ticket is open, belongs to a watched component, and has had no engineer comment for more than N days (configurable)

**Private delivery options (TBD):**
- **Jira internal comment** — post with a specific prefix (e.g. `[AI-DRAFT]`) that the team treats as internal-only; simplest, no new infrastructure
- **Slack DM** — send the draft analysis directly to the ticket assignee via the Slack bot
- **Local report file** — append to a daily digest file on disk; low-tech but useful for batch review
- **Email** — send to assignee or team alias; requires SMTP setup

**Approval flow (TBD):**
- Dev reviews the draft and either approves (posts publicly), discards, or edits before posting
- Approval mechanism could be a Jira comment reply, a Slack reaction, or a simple CLI command
