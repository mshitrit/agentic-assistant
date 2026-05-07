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

---

## 2. Slack Consent Flow Before AI Analysis

**Summary:** Before triggering any AI analysis, the bot sends a disclaimer message with Confirm / Cancel buttons, ensuring users are aware they are interacting with an AI and do not share sensitive information unintentionally.

**Motivation:** Users may not realise their message is being passed to an external AI service. An explicit confirmation step improves transparency and reduces the risk of accidental data disclosure.

**Implementation notes:**
- Use Slack Block Kit interactive buttons (`confirm_analysis` / `cancel_analysis` action IDs)
- Encode the question in the button `value` field to avoid server-side state (2000 char limit applies)
- Enable **Interactivity** in the Slack app settings (no additional OAuth scopes needed — Socket Mode handles callbacks)
- Skip the confirmation step for thread follow-ups where the user has already confirmed once

---

## 3. Slack Answer Quality Feedback and Memory Correction

**Summary:** When a Slack thread reveals that an initial AI answer was wrong or incomplete, allow the corrected answer to influence future responses — so new threads asking the same question get the right answer from the start.

**Motivation:** Currently each thread is stateless. If a user corrects the bot mid-thread, the correction improves that thread's answers (via context inheritance) but is lost to all future threads. This creates a frustrating experience where the same wrong answer is repeatedly given to new users asking the same question.

**Possible approaches (TBD):**

- **Manual memory update via command** — a designated user posts `/update-memory` in the thread, prompting the bot to summarise the corrected answer and write it to living memory via `write_memory_file`. Simple and human-controlled.
- **Implicit correction detection** — the bot detects phrases like "actually, that's wrong" or "the correct answer is..." in follow-up messages and automatically triggers a living memory update. More seamless but higher risk of spurious updates.
- **Periodic human review** — no automatic update; instead, team members periodically review thread history for corrections and manually update verified memory. Lowest automation, highest accuracy.

**Recommended approach:** Manual trigger (`/update-memory`) to keep humans in control, with the bot drafting the memory update for review before committing. This balances automation with accuracy and aligns with the existing verified/living memory review workflow.
