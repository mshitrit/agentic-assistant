import anthropic
from config.settings import GCP_PROJECT, GCP_REGION, DEBUG_MODE, DebugMode


def ask_agent(context: dict) -> str:
    if DebugMode.DISABLE_AI in DEBUG_MODE:
        return f"[DEBUG] AI disabled. Ticket '{context.get('title')}' requested AI analysis."
    client = anthropic.AnthropicVertex(project_id=GCP_PROJECT, region=GCP_REGION)
    prompt = (
        f"A Jira ticket titled '{context.get('title')}' has been flagged for AI analysis. "
        f"Briefly acknowledge this and suggest a next action in 1-2 sentences."
    )
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text
