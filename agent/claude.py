import anthropic
from config.settings import (
    AGENT_MODEL, DEBUG_MODE, DebugMode, LOG_LEVEL,
    MAX_READ_CALLS, MAX_WRITE_CALLS, PR_WORKFLOW_MAX_TOKENS,
)
from agent.prompts import AgentMode, build_prompt, parse_workflow_outcome
from agent.tools import (
    PR_WORKFLOW_TOOLS, TOOL_DEFINITIONS,
    read_file, list_directory, write_memory_file, write_repo_file,
)
from agent.vertex import AgentResult, extract_response_text, get_vertex_client

READ_TOOLS  = {"read_file", "list_directory"}
WRITE_TOOLS = {"write_memory_file"}
REPO_WRITE_TOOLS = {"write_repo_file"}

TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_directory": list_directory,
    "write_memory_file": write_memory_file,
    "write_repo_file": write_repo_file,
}

_NUDGE_MISSING_OUTCOME = (
    "Your response must end with exactly one outcome line: "
    "`OUTCOME: implement` (after calling write_repo_file for each changed file) or "
    "`OUTCOME: no_code_change` (with a brief reason if no repo edits are needed)."
)

_NUDGE_IMPLEMENT_WITHOUT_WRITES = (
    "You indicated that code changes are required (`OUTCOME: implement`) but have not "
    "called write_repo_file yet. Read any files you still need, then call write_repo_file "
    "with full file contents for each file to edit. If you no longer believe a code change "
    "is needed, end with `OUTCOME: no_code_change` and a brief reason."
)


def _workflow_turn_done(
    text: str,
    repo_write_count: int,
    *,
    outcome_nudges: int,
    implement_nudges: int,
) -> tuple[bool, str | None, int, int]:
    """Return (done, nudge_message, new_outcome_nudges, new_implement_nudges)."""
    outcome = parse_workflow_outcome(text)

    if outcome == "no_code_change":
        return True, None, outcome_nudges, implement_nudges

    if outcome == "implement":
        if repo_write_count > 0:
            return True, None, outcome_nudges, implement_nudges
        if implement_nudges < 2:
            return False, _NUDGE_IMPLEMENT_WITHOUT_WRITES, outcome_nudges, implement_nudges + 1
        return True, None, outcome_nudges, implement_nudges

    if outcome_nudges < 1:
        return False, _NUDGE_MISSING_OUTCOME, outcome_nudges + 1, implement_nudges
    return True, None, outcome_nudges, implement_nudges


def _create_message(
    client: anthropic.AnthropicVertex,
    *,
    model: str,
    max_tokens: int,
    tools: list,
    messages: list,
    stream: bool,
) -> anthropic.types.Message:
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "tools": tools,
        "messages": messages,
    }
    if stream:
        with client.messages.stream(**kwargs) as stream_mgr:
            return stream_mgr.get_final_message()
    return client.messages.create(**kwargs)


def _execute_tool(
    block,
    *,
    workflow_mode: bool,
    repo_path: str,
    operator: str,
    read_count: int,
    write_count: int,
) -> tuple[str, bool, int, int]:
    """Run one tool; return (result_text, repo_write_ok, new_read_count, new_write_count)."""
    is_read = block.name in READ_TOOLS
    is_write = block.name in WRITE_TOOLS
    is_repo_write = block.name in REPO_WRITE_TOOLS
    repo_write_ok = False

    if not workflow_mode and is_read and read_count >= MAX_READ_CALLS:
        print(f"[WARNING] Read tool limit ({MAX_READ_CALLS}) reached.")
        return (
            f"Error: read tool limit of {MAX_READ_CALLS} reached. "
            "Use remaining write budget or provide your final answer.",
            False,
            read_count,
            write_count,
        )
    if not workflow_mode and is_write and write_count >= MAX_WRITE_CALLS:
        print(f"[WARNING] Write tool limit ({MAX_WRITE_CALLS}) reached.")
        return (
            f"Error: write tool limit of {MAX_WRITE_CALLS} reached. "
            "Provide your final answer now.",
            False,
            read_count,
            write_count,
        )

    fn = TOOL_FUNCTIONS.get(block.name)
    if fn is None:
        return f"Error: unknown tool '{block.name}'", False, read_count, write_count

    if LOG_LEVEL == "DEBUG":
        print(f"[TOOL CALL] {block.name}({block.input})")

    inp = dict(block.input)
    if block.name == "write_repo_file":
        if not inp.get("file_path"):
            return (
                "Error: write_repo_file requires file_path and content.",
                False,
                read_count,
                write_count,
            )
        if inp.get("content") is None:
            return (
                "Error: write_repo_file missing content (tool input may be truncated). "
                "Retry with the full file content in the content field.",
                False,
                read_count,
                write_count,
            )

    extra = {}
    if block.name in READ_TOOLS | REPO_WRITE_TOOLS:
        extra["repo_path"] = repo_path
    if is_write and operator:
        fn_path = inp.get("filename", "")
        if fn_path and not fn_path.startswith(f"{operator}/"):
            inp["filename"] = f"{operator}/{fn_path}"

    try:
        result = fn(**inp, **extra)
    except TypeError as e:
        result = f"Error: tool call failed: {e}"

    if LOG_LEVEL == "DEBUG":
        preview = result[:200] + ("..." if len(result) > 200 else "")
        print(f"[TOOL RESULT] {preview}")

    if is_repo_write and not str(result).startswith("Error:"):
        repo_write_ok = True
    if not workflow_mode and is_read:
        read_count += 1
    elif not workflow_mode and is_write:
        write_count += 1

    return result, repo_write_ok, read_count, write_count


def ask_agent(
    context: dict,
    mode: AgentMode = AgentMode.JIRA,
    repo_path: str = "",
    operator: str = "",
    op_name: str = "",
    *,
    base_branch: str = "main",
    branch_name: str = "",
    user_instructions: str = "",
) -> AgentResult:
    if DebugMode.DISABLE_AI in DEBUG_MODE:
        return AgentResult(response=f"[DEBUG] AI disabled. Ticket '{context.get('title')}' requested AI analysis.")

    workflow_mode = mode in (AgentMode.PR_WORKFLOW_JIRA, AgentMode.PR_WORKFLOW_GITHUB)
    try:
        client = get_vertex_client()
        prompt = build_prompt(
            context, mode, operator=operator, op_name=op_name,
            repo_path=repo_path, base_branch=base_branch, branch_name=branch_name,
            user_instructions=user_instructions,
        )

        if LOG_LEVEL == "DEBUG":
            print(f"\n--- Agent Prompt ---\n{prompt}\n--- End Prompt ---\n")

        messages = [{"role": "user", "content": prompt}]
        tools = (PR_WORKFLOW_TOOLS if workflow_mode else TOOL_DEFINITIONS) if repo_path else []
        read_count = 0
        write_count = 0
        repo_write_count = 0
        outcome_nudges = 0
        implement_nudges = 0

        while True:
            response = _create_message(
                client,
                model=AGENT_MODEL,
                max_tokens=PR_WORKFLOW_MAX_TOKENS if workflow_mode else 1024,
                tools=tools,
                messages=messages,
                stream=workflow_mode,
            )

            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            if tool_use_blocks:
                if response.stop_reason != "tool_use":
                    print(
                        f"[WARNING] Response contains {len(tool_use_blocks)} tool_use block(s) "
                        f"but stop_reason={response.stop_reason!r}; running tools anyway."
                    )

                tool_results = []
                for block in tool_use_blocks:
                    result, repo_write_ok, read_count, write_count = _execute_tool(
                        block,
                        workflow_mode=workflow_mode,
                        repo_path=repo_path,
                        operator=operator,
                        read_count=read_count,
                        write_count=write_count,
                    )
                    if repo_write_ok:
                        repo_write_count += 1
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
                continue

            text = extract_response_text(response) or "[No response]"
            if workflow_mode:
                done, nudge, outcome_nudges, implement_nudges = _workflow_turn_done(
                    text,
                    repo_write_count,
                    outcome_nudges=outcome_nudges,
                    implement_nudges=implement_nudges,
                )
                if not done and nudge:
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": nudge})
                    continue
                if (
                    parse_workflow_outcome(text) == "implement"
                    and repo_write_count == 0
                ):
                    return AgentResult(
                        response=text,
                        error="no_repo_writes",
                    )
            return AgentResult(response=text)

    except anthropic.RateLimitError as e:
        print(f"[ERROR] ask_agent rate limited: {e}")
        return AgentResult(error="rate_limit")
    except anthropic.APIError as e:
        print(f"[ERROR] ask_agent API error: {e}")
        return AgentResult(error="api_error")
    except Exception as e:
        print(f"[ERROR] ask_agent unexpected error: {e}")
        return AgentResult(error="api_error")
