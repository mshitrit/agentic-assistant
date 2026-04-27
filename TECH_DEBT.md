# Technical Debt

## 1. Replace Polling with Jira Webhook

**Priority: High**

**Current approach:** `main.py` polls Jira every 20 seconds to check for trigger conditions.

**Why polling was chosen:** Webhook registration requires Jira admin permissions, which were not available. Polling was used as a simpler alternative sufficient for PoC purposes.

**Why this is debt:**
- Inefficient — makes API calls every cycle regardless of activity
- Reaction time bounded by poll interval (currently 20s)
- Higher API usage, potential rate limiting at scale

## 2. Designated Jira Account for the AI Agent

**Priority: High**

**Current approach:** The agent posts comments using a personal user account (configured via `JIRA_USER`/`JIRA_TOKEN`).

**Why this is debt:**
- Comments appear as coming from a real user, making it hard to distinguish AI-generated activity from human activity at a glance
- Ties the agent to a specific person's credentials

**Desired solution:** Create a dedicated Jira service account for the agent (e.g. `ai-agent@redhat.com`). This makes AI activity clearly identifiable in the audit trail and decouples the agent from any individual's account.

## 3. Comment Pagination

**Priority: Low**

**Current approach:** Comments are fetched as part of the issue details request (`GET /issue/{key}?fields=comment`), which returns up to 100 comments by default — sufficient for typical ticket volumes.

**Why this is debt:**
- Trigger detection (`/ai-assist` comment) and AI comment deduplication could silently fail on tickets with more than 100 comments
- Agent analysis may be incomplete on very active tickets where key findings appear beyond comment 100

**Desired solution:** Fetch comments via the dedicated paginated endpoint (`GET /rest/api/3/issue/{key}/comment`) if this ever becomes a real concern at scale.

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

## 5. SBR Local Repo Staleness

**Priority: Medium**

**Current approach:** `SBR_REPO_PATH` points to a manually maintained local clone of the SBR repo.

**Why this is debt:**
- The local clone can drift from the actual codebase if not kept up to date
- A stale clone undermines the agent's ability to detect memory drift (Step 4) and provide accurate code references

**Desired solution:** Automate repo sync — e.g. a periodic `git pull` via cron job, or trigger a pull at agent startup if the last sync was more than N hours ago.

## 6. Migrate Tool Integration to MCP (Model Context Protocol)

**Current approach:** Tools (`read_file`, `list_directory`, `write_memory_file`) are defined manually in `agent/tools.py` with hand-written JSON schemas, and the tool call/result loop is implemented by hand in `agent/claude.py`.

**Why this is debt:**
- Tool schemas must be kept in sync with function signatures by hand
- The tool loop, dispatch logic, and debug logging are all custom boilerplate
- Adding new tools requires changes in both `tools.py` and `claude.py`
- Tools are not reusable across other agents without copy-pasting

**Desired solution:** Migrate to MCP — expose tools via a dedicated MCP server and use the MCP client for tool discovery. This reduces boilerplate and makes tools reusable across agents and models.

**Caveats before migrating:**
- The current split read/write call limits (`MAX_READ_CALLS` / `MAX_WRITE_CALLS`) and per-call debug logging (`[TOOL CALL]` / `[TOOL RESULT]`) require running a hybrid loop (own loop + MCP for schema discovery) or moving limit enforcement into the MCP server itself.
- Not worth migrating until the project has more tools or multiple agents that could share them.

**Priority:** Low — current implementation works well for the current scope.

## 7. Add Automated Tests

**Priority: Medium**

**Current approach:** No automated tests exist. The project has been validated manually by running against real Jira tickets.

**Why this is debt:**
- No safety net for regressions when modifying prompt logic, tool wiring, or Jira client code
- Hard to verify edge cases (e.g. comment pagination, ADF parsing, tool call limits) without a live Jira instance

**Desired solution:** Add unit tests for at minimum:
- `jira/utils.py` — ADF text extraction
- `jira/comments.py` — comment detection and deduplication logic
- `agent/tools.py` — path traversal guards, tool limit enforcement
- `agent/prompts.py` — prompt structure given various memory states

Use `pytest` with mocked HTTP responses (`responses` or `unittest.mock`) to avoid live API calls.

## 8. Jira Comment Formatting

**Priority: Low**

**Current approach:** The agent's response is posted as plain text, so Markdown syntax (e.g. `**bold**`, `## headers`, ` ``` code blocks`) appears literally in Jira instead of being rendered.

**Why this is debt:**
- Comments are harder to read — formatting intended to aid clarity is shown as raw symbols
- Jira uses Atlassian Document Format (ADF) for rich text, not Markdown

**Desired solution:** Convert the agent's Markdown response to ADF before posting. A lightweight conversion (headers → ADF headings, bold → ADF strong, bullet lists → ADF bullet lists) in `jira/comments.py` would cover the most common cases. Libraries like `markdown-it-py` or a custom converter could be used.

## 9. Security & Compliance Review

**Priority: Blocker**

**Why this is a blocker:**
Before this project is used beyond personal PoC scope (shared with a team, run against real production tickets, or expanded to Slack), the following questions must be answered:

**1. Red Hat AI Tool Approval Process**
- Does this qualify as a new internal AI tool requiring formal approval through Red Hat's AI governance pipeline?
- Red Hat has processes for reviewing AI-assisted tools used internally — this project may need to go through that process before broader use.

**2. Privacy & Data Classification**
- Jira tickets, comments, and descriptions may contain Red Hat-confidential or customer-sensitive information.
- This data is currently passed to Claude via GCP Vertex AI. It must be confirmed that:
  - This is compliant with Red Hat's data classification policy
  - GCP Vertex AI is an approved data processor for this class of data
  - Internal-only Jira comments are not inadvertently exposed to the AI

**Desired solution:** Raise both questions with the appropriate Red Hat legal/security/AI governance team before expanding scope. Document the outcome here.
