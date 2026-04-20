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

## 3. Comment Pagination

**Current approach:** Comments are fetched as part of the issue details request, which returns only the first 10 comments by default.

**Why this is debt:**
- Trigger detection (`/ai-assist` comment) may miss the trigger if it's beyond the first 10 comments
- AI comment deduplication check may fail on tickets with many comments
- Agent analysis may be incomplete — comments often contain key investigation findings, workarounds, and engineer discussions that inform a meaningful response

**Desired solution:** Fetch comments via the dedicated paginated endpoint (`GET /rest/api/3/issue/{key}/comment`) to ensure all comments are checked.

## 4. Prompt Size / Claude Cost Optimization

**Current approach:** Every Claude request includes the full verified memory (~5 files, ~850 lines) regardless of ticket content.

**Why this is debt:**
- Input token cost scales with every request, even for simple tickets
- Memory files change rarely but are re-read and re-sent on every single trigger

**Desired solution (options, increasing complexity):**
- **Selective injection** — only include memory sections relevant to the ticket's components/keywords
- **Prompt caching** — use Anthropic's prompt caching API for the static memory prefix (charged at a fraction of normal input token price)
- **Tiered models** — use a cheaper model (Sonnet/Haiku) for routine tickets, Opus only for complex ones

**Cost analysis (current implementation):**
- Input: ~8,500–10,000 tokens per request (dominated by the ~850-line verified memory, re-sent on every trigger)
- Output: ~200–500 tokens per response
- Estimated cost: ~$0.17 per request at Opus pricing (~$15/MTok input, ~$75/MTok output on Vertex AI)
- At typical PoC volume (tens of requests/month) this is negligible; only becomes a concern above ~1,000 requests/month (~$170/month)

**Priority: Low** — cost is acceptable at current scale. Revisit if request volume grows significantly.
