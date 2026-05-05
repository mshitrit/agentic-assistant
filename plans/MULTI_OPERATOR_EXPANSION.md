# Multi-Operator Expansion Plan

**Goal:** Extend the agent to support multiple medik8s operators beyond SBR, with per-operator memory, repo access, and prompt context.

---

## Step 1: Operator Registry in Config

Replace the current single-operator config fields (`COMPONENTS`, `SBR_REPO_PATH`) with a per-operator structure in `config/config.txt`:

```
OPERATOR_SBR_COMPONENTS=Storage-based Remediation
OPERATOR_SBR_REPO_PATH=/home/.../storage-based-remediation

OPERATOR_FAR_COMPONENTS=Fence Agents Remediation
OPERATOR_FAR_REPO_PATH=/home/.../fence-agents-remediation
```

Update `config/settings.py` to parse these into a dict keyed by operator name:

```python
OPERATORS = {
    "sbr": {"components": [...], "repo_path": "..."},
    "far": {"components": [...], "repo_path": "..."},
}
```

---

## Step 2: Operator Detection Per Ticket

When a ticket is fetched, determine which operator it belongs to by matching its Jira components against each operator's component list.

- Add a `detect_operator(fields: dict) -> str | None` function in `jira/utils.py`
- Returns the operator key (e.g. `"sbr"`) or `None` if no match
- Pass the detected operator through to the agent context

---

## Step 3: Per-Operator Memory Loading

The memory structure already supports multiple operators (`memory/verified/{operator}/`, `memory/living/{operator}/`).

Update `agent/prompts.py` to accept an `operator` parameter and load only that operator's memory directory instead of the full `verified/` and `living/` trees.

---

## Step 4: Dynamic Prompt Persona

The prompt currently hardcodes `"SBR (Storage-Based Remediation) engineer"`.

Update `build_jira_prompt` and `build_slack_prompt` to accept an `operator` parameter and inject the correct operator name and description into the persona line.

Maintain a small operator metadata dict (name, description) — either in `config/settings.py` or a new `agent/operators.py`.

---

## Step 5: Per-Operator Repo Access in Tools

`agent/tools.py` currently reads `SBR_REPO_PATH` from settings as a single global.

Update `read_file` and `list_directory` to accept a `repo_path` parameter (or read it from a context object) so the correct operator repo is used per ticket.

---

## Step 6: Jira Fetching

Update `fetch_issues_by_components` to fetch all components across all operators in a single JQL query (already works — just pass the combined component list).

Alternatively, fetch per operator and tag results with operator key at fetch time.

---

## Step 7: Populate Verified Memory for New Operators

For each new operator added, populate its verified memory by running the agent against the operator's codebase — same process used to populate `memory/verified/sbr/`.

Files to create per operator:
- `overview.md`
- `architecture.md`
- `failure_modes.md`
- `runbook.md`
- `code_map.md`

---

## Step 8: Copy Living Memory

After populating verified memory for each new operator:
```bash
cp -r memory/verified/{operator}/ memory/living/{operator}/
```

---

## Step 9: Slack Bot Operator Detection

Since all operators share a single support channel, the Slack bot must determine operator context from the user's message using an explicit prefix.

### Format

Users prefix their question with the operator name in square brackets:

```
@bot [SBR] how does fencing work?
@bot [FAR] how does FAR handle the same scenario?
```

### Thread-Start Behaviour (`is_thread_reply == False`)

1. Parse `[OPERATOR]` from the current message.
2. If missing or not a recognised operator → reply with a clear error message listing valid operators. Do **not** call the agent.
3. If valid → proceed. The "Analysing..." message must confirm the operator context:
   `"Analysing your question about *SBR*, please wait..."`

### Thread Follow-Up Behaviour (`is_thread_reply == True`)

1. Fetch thread history as usual.
2. Scan user messages in **reverse chronological order** (skipping bot messages) for the most recent valid `[OPERATOR]` tag.
3. Use that operator as context — this means a user can switch operator mid-thread by prefixing a follow-up with a different tag.
4. If no `[OPERATOR]` tag is found in any user message (edge case — should not happen since the first message is validated), fall back gracefully with an error.
5. The "Analysing..." message confirms the active operator:
   `"Analysing your follow-up question about *SBR*, please wait..."`

**Example thread:**
```
User:  [SBR] how does fencing work?          → operator: SBR
Bot:   ...
User:  can you elaborate on the watchdog?    → operator: SBR (inherited)
Bot:   ...
User:  [FAR] how does FAR handle the same?  → operator: FAR (switched)
Bot:   ...
User:  what about timeouts?                  → operator: FAR (last specified)
```

### Components to Update

| Component | Change |
|---|---|
| `slack/client.py` | Add `extract_operator_from_thread(messages, bot_user_id) -> str \| None` — scans messages in reverse, skips bot messages, returns first valid `[OPERATOR]` tag found |
| `slack_bot_main.py` | Parse operator at thread start; call `extract_operator_from_thread` for follow-ups; include operator in "Analysing..." message |
| `agent/prompts.py` | Accept `operator` param in `build_slack_prompt` and `build_slack_thread_prompt`; load operator-specific memory dir; inject operator name into persona line |
| `agent/tools.py` | Accept `repo_path` param (or operator key) in `read_file` / `list_directory` to use the correct operator repo |
| `agent/claude.py` | Pass operator context through to prompt builder and tool functions |
