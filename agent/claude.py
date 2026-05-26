import anthropic
from config.settings import (
    AGENT_MODEL, DEBUG_MODE, DebugMode, LOG_LEVEL,
    MAX_READ_CALLS, MAX_WRITE_CALLS, PR_REVIEW_MAX_TOKENS,
)
from agent.prompts import build_prompt, AgentMode
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


def ask_agent(
    context: dict,
    mode: AgentMode = AgentMode.JIRA,
    repo_path: str = "",
    operator: str = "",
    op_name: str = "",
    *,
    base_branch: str = "main",
    branch_name: str = "",
) -> AgentResult:
    if DebugMode.DISABLE_AI in DEBUG_MODE:
        return AgentResult(response=f"[DEBUG] AI disabled. Ticket '{context.get('title')}' requested AI analysis.")

    pr_mode = mode == AgentMode.PR_WORKFLOW_JIRA
    try:
        client = get_vertex_client()
        prompt = build_prompt(
            context, mode, operator=operator, op_name=op_name,
            repo_path=repo_path, base_branch=base_branch, branch_name=branch_name,
        )

        if LOG_LEVEL == "DEBUG":
            print(f"\n--- Agent Prompt ---\n{prompt}\n--- End Prompt ---\n")

        messages = [{"role": "user", "content": prompt}]
        tools = (PR_WORKFLOW_TOOLS if pr_mode else TOOL_DEFINITIONS) if repo_path else []
        read_count  = 0
        write_count = 0

        while True:
            response = client.messages.create(
                model=AGENT_MODEL if pr_mode else "claude-opus-4-5",
                max_tokens=PR_REVIEW_MAX_TOKENS if pr_mode else 1024,
                tools=tools,
                messages=messages,
            )

            if response.stop_reason != "tool_use":
                return AgentResult(response=extract_response_text(response) or "[No response]")

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                is_read  = block.name in READ_TOOLS
                is_write = block.name in WRITE_TOOLS

                if not pr_mode and is_read and read_count >= MAX_READ_CALLS:
                    print(f"[WARNING] Read tool limit ({MAX_READ_CALLS}) reached.")
                    result = f"Error: read tool limit of {MAX_READ_CALLS} reached. Use remaining write budget or provide your final answer."
                elif not pr_mode and is_write and write_count >= MAX_WRITE_CALLS:
                    print(f"[WARNING] Write tool limit ({MAX_WRITE_CALLS}) reached.")
                    result = f"Error: write tool limit of {MAX_WRITE_CALLS} reached. Provide your final answer now."
                else:
                    fn = TOOL_FUNCTIONS.get(block.name)
                    if fn is None:
                        result = f"Error: unknown tool '{block.name}'"
                    else:
                        if LOG_LEVEL == "DEBUG":
                            print(f"[TOOL CALL] {block.name}({block.input})")
                        inp = dict(block.input)
                        extra = {}
                        if block.name in READ_TOOLS | REPO_WRITE_TOOLS:
                            extra["repo_path"] = repo_path
                        if is_write and operator:
                            fn_path = inp.get("filename", "")
                            if fn_path and not fn_path.startswith(f"{operator}/"):
                                inp["filename"] = f"{operator}/{fn_path}"
                        result = fn(**inp, **extra)
                        if LOG_LEVEL == "DEBUG":
                            print(f"[TOOL RESULT] {result[:200]}{'...' if len(result) > 200 else ''}")
                        if not pr_mode and is_read:
                            read_count += 1
                        elif not pr_mode and is_write:
                            write_count += 1

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

    except anthropic.RateLimitError as e:
        print(f"[ERROR] ask_agent rate limited: {e}")
        return AgentResult(error="rate_limit")
    except anthropic.APIError as e:
        print(f"[ERROR] ask_agent API error: {e}")
        return AgentResult(error="api_error")
    except Exception as e:
        print(f"[ERROR] ask_agent unexpected error: {e}")
        return AgentResult(error="api_error")
