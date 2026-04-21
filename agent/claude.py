import anthropic
from config.settings import GCP_PROJECT, GCP_REGION, DEBUG_MODE, DebugMode, LOG_LEVEL, MAX_READ_CALLS, MAX_WRITE_CALLS, SBR_REPO_PATH
from agent.prompts import build_prompt
from agent.tools import TOOL_DEFINITIONS, read_file, list_directory, write_memory_file

READ_TOOLS  = {"read_file", "list_directory"}
WRITE_TOOLS = {"write_memory_file"}

TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_directory": list_directory,
    "write_memory_file": write_memory_file,
}


def ask_agent(context: dict) -> str:
    if DebugMode.DISABLE_AI in DEBUG_MODE:
        return f"[DEBUG] AI disabled. Ticket '{context.get('title')}' requested AI analysis."

    client = anthropic.AnthropicVertex(project_id=GCP_PROJECT, region=GCP_REGION)
    prompt = build_prompt(context)

    if LOG_LEVEL == "DEBUG":
        print(f"\n--- Agent Prompt ---\n{prompt}\n--- End Prompt ---\n")

    messages = [{"role": "user", "content": prompt}]
    tools = TOOL_DEFINITIONS if SBR_REPO_PATH else []
    read_count  = 0
    write_count = 0

    while True:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            text_blocks = [b.text for b in response.content if hasattr(b, "text")]
            return "\n".join(text_blocks) or "[No response]"

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            is_read  = block.name in READ_TOOLS
            is_write = block.name in WRITE_TOOLS

            if is_read and read_count >= MAX_READ_CALLS:
                print(f"[WARNING] Read tool limit ({MAX_READ_CALLS}) reached.")
                result = f"Error: read tool limit of {MAX_READ_CALLS} reached. Use remaining write budget or provide your final answer."
            elif is_write and write_count >= MAX_WRITE_CALLS:
                print(f"[WARNING] Write tool limit ({MAX_WRITE_CALLS}) reached.")
                result = f"Error: write tool limit of {MAX_WRITE_CALLS} reached. Provide your final answer now."
            else:
                fn = TOOL_FUNCTIONS.get(block.name)
                if fn is None:
                    result = f"Error: unknown tool '{block.name}'"
                else:
                    if LOG_LEVEL == "DEBUG":
                        print(f"[TOOL CALL] {block.name}({block.input})")
                    result = fn(**block.input)
                    if LOG_LEVEL == "DEBUG":
                        print(f"[TOOL RESULT] {result[:200]}{'...' if len(result) > 200 else ''}")
                    if is_read:
                        read_count += 1
                    elif is_write:
                        write_count += 1

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result
            })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
