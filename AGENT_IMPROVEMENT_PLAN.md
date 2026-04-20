# Agent Improvement Plan

Steps to evolve the agent from a basic responder to a meaningful SBR ticket analyser.

## Step 1: Enrich Jira Ticket Data
Expand `get_issue_details()` to fetch additional fields per ticket:
- `description` — ticket body
- `status` — current workflow state
- `priority` — urgency signal
- `assignee` — ticket owner
- `issuetype` — Bug, Story, Task, etc.
- `components` — area of the system

## Step 2: Build a Structured Ticket Context Object
Instead of passing only the ticket title to `ask_agent()`, pass a structured dict containing all enriched fields from Step 1.

## Step 3: Add SBR Domain Knowledge via System Prompt
Inject a static description of what SBR is — its purpose, architecture, key concepts, and common failure modes — as a `system` message in every Claude call. This gives the agent baseline domain understanding without additional infrastructure.

## Step 4: Provide Codebase Context via GitHub
Since SBR is open source, reference the GitHub repository URL in the system prompt. For deeper per-ticket analysis, fetch relevant source files dynamically using the public GitHub API and include them in the prompt.

## Step 5: Include Recent Git History for Relevant Files
For bug tickets, fetch the last N commits touching files related to the ticket using the GitHub public API. Include these diffs in the prompt to give the agent signal about recent changes that may be relevant.

## Step 6: Improve the Prompt
Using all of the above context, construct a role-anchored prompt:
> "You are an SBR engineer. Given the following ticket details and relevant code context, provide a concise analysis and suggest next steps."

## Step 7: Extract Prompt Construction to `agent/prompts.py`
Once the prompt grows to incorporate domain knowledge, ticket context, and code snippets, move prompt construction to a dedicated file to keep `agent/claude.py` focused on the API call only.

## Step 8: Test and Iterate
Use `DEBUG_MODE=DISABLE_JIRA` to test agent responses without posting to Jira. Iterate on prompt wording and context selection based on output quality.
