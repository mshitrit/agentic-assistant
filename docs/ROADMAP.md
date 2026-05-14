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

---

## 4. Co-locate Operator Knowledge with Upstream Repos

**Summary:** Make each medik8s operator repository the **single source of truth** for its AI-oriented markdown (e.g. under `docs/agent-memory/` or `docs/ai-context/`). Agentic-assistant **stops maintaining a duplicate** `memory/verified/<operator>/` tree in this repo and instead **loads** that content from the path already configured as `OPERATOR_*_REPO_PATH` (plus tooling and prompt changes so Jira/Slack still receive the same material).

**Motivation:** One place to update when code or layout changes; PRs can review behaviour and operator-local docs together. Avoids ongoing drift and removes the need to keep two copies in sync.

**Implementation notes (TBD):**

- **Layout and naming** — Agree on a fixed relative path and file set per operator (overview, architecture, code map, runbook, failure modes, or a slimmer bundle).
- **Prompt assembly** — Extend `agent/prompts.py` (and any callers) to read verified files from the operator checkout instead of `memory/verified/`.
- **Living memory** — Decide whether agent-written updates still land only under `memory/living/` here, or gain an operator-local path with explicit promotion into that repo’s docs.
- **Bootstrap / deploy** — `deploy.sh` and onboarding docs should assume each operator clone includes the doc subtree (or fails fast with a clear message).

**Open questions:** Governance (who approves merges to “verified” content on the operator side), versioning across branches, and behaviour when a configured `REPO_PATH` is missing or shallow-cloned.

**Recommended first step:** Pilot on **one** operator: add the doc subtree there, wire agentic-assistant to read only from that checkout for that operator, delete the in-repo `memory/verified/<pilot>/` copy once parity is checked, then repeat for the rest.
