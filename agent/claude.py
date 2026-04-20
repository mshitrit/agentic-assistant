import anthropic
from config.settings import GCP_PROJECT, GCP_REGION, DEBUG_MODE, DebugMode
from agent.prompts import build_prompt


def ask_agent(context: dict) -> str:
    if DebugMode.DISABLE_AI in DEBUG_MODE:
        return f"[DEBUG] AI disabled. Ticket '{context.get('title')}' requested AI analysis."
    client = anthropic.AnthropicVertex(project_id=GCP_PROJECT, region=GCP_REGION)
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": build_prompt(context)}]
    )
    return message.content[0].text
