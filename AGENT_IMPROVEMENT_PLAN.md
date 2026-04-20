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

## Step 3: Build Verified Memory (SBR Domain Knowledge)
Create a `memory/verified/` directory in this repo containing human-curated summaries of SBR:
- Purpose and architecture overview
- Key components and their responsibilities
- Common failure modes and known issues

This content is manually authored (with AI assistance) from the SBR repo and docs, committed to git, and treated as the stable, human-approved knowledge base. The agent always consults it as a baseline.

## Step 4: Build Living Memory (Agent-Maintained Knowledge)
Create a `memory/living/` directory mirroring the structure of `memory/verified/`. This copy is owned by the agent — it may update it during ticket analysis if it detects a discrepancy between the verified content and what it observes in the current SBR codebase.

Updates happen **on the fly** during ticket analysis (not via a scheduled job): if the agent is already reading relevant SBR code and notices something has changed, it updates the corresponding living memory file as a side effect. Updates are logged so the human review has a clear audit trail.

## Step 5: Human Review and Memory Alignment
Periodically, a user reviews the diff between `memory/living/` and `memory/verified/`. If the living memory changes are correct, the user commits them into `memory/verified/`, effectively promoting agent-learned knowledge to the verified baseline.

## Step 6: Improve the Prompt
Using all of the above context, construct a role-anchored prompt:
> "You are an SBR engineer. Given the following ticket details, verified domain knowledge, and any recent observations from living memory, provide a concise analysis and suggest next steps."

## Step 7: Extract Prompt Construction to `agent/prompts.py`
Once the prompt grows to incorporate domain knowledge, ticket context, and code snippets, move prompt construction to a dedicated file to keep `agent/claude.py` focused on the API call only.

## Step 8: Test and Iterate
Use `DEBUG_MODE=DISABLE_JIRA` to test agent responses without posting to Jira. Iterate on prompt wording and context selection based on output quality.
