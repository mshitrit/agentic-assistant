# Multi-Operator Expansion Plan

**Goal:** Extend the agent to support multiple medik8s operators beyond SBR, with per-operator memory, repo access, and prompt context.

---

## ✅ Step 1: Operator Registry in Config

Replace the single-operator config fields (`COMPONENTS`, `SBR_REPO_PATH`) with a per-operator structure in `config/config.txt`:

```
OPERATOR_SBR_COMPONENTS=Storage-based Remediation
OPERATOR_SBR_REPO_PATH=/home/user/gitRepos/medik8s/storage-based-remediation
```

`config/settings.py` parses these into an `OPERATORS` dict keyed by operator name:

```python
OPERATORS = {
    "sbr": {"components": ["Storage-based Remediation"], "repo_path": "..."},
}
```

---

## ✅ Step 2: Operator Detection Per Ticket

`detect_operator(fields, operators)` in `jira/utils.py` matches a ticket's Jira components against each operator's component list and returns the operator key (e.g. `"sbr"`) or `None`. Tickets with no matching operator are skipped with a console warning.

---

## ✅ Step 3: Per-Operator Memory Loading

`build_jira_prompt` in `agent/prompts.py` loads memory from `memory/verified/{operator}/` and `memory/living/{operator}/` when an operator is provided, scoping context to only the relevant operator's knowledge.

---

## ✅ Step 4: Dynamic Prompt Persona

`build_jira_prompt` constructs the persona line dynamically using the operator's first component name (e.g. `"You are an experienced Storage-based Remediation engineer."`), removing the hardcoded SBR reference.

---

## ✅ Step 5: Per-Operator Repo Access in Tools

`read_file` and `list_directory` in `agent/tools.py` accept a `repo_path` parameter. `ask_agent` in `agent/claude.py` receives `repo_path` derived from `OPERATORS[operator]["repo_path"]` and passes it to tool calls.

---

## Step 6: Jira Fetching Verification

Verify that the multi-operator JQL query works correctly end-to-end:
- All operator components are combined into a single `component in (...)` JQL clause
- Ticket counts match expectations across operators
- Operator detection correctly routes each ticket

---

## Step 7: Slack Bot Operator Detection

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

---

## Step 8: Per-Operator Memory and Persona for Slack

Update `build_slack_prompt` and `build_slack_thread_prompt` in `agent/prompts.py` to accept `operator` and `op_name` parameters — same pattern as `build_jira_prompt`. Update `build_prompt` and `ask_agent` to pass them through from `slack_bot_main.py`.

---

## Step 9: Populate Verified Memory for New Operators

For each new operator added, populate its verified memory by running the agent against the operator's codebase — same process used to populate `memory/verified/sbr/`.

Files to create per operator:
- `overview.md`
- `architecture.md`
- `failure_modes.md`
- `runbook.md`
- `code_map.md`

---

## Step 10: Copy Living Memory

After populating verified memory for each new operator:
```bash
cp -r memory/verified/{operator}/ memory/living/{operator}/
```
