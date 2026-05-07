import re


def get_bot_user_id(client) -> str:
    return client.auth_test()["user_id"]


def fetch_thread_messages(client, channel: str, thread_ts: str) -> list:
    result = client.conversations_replies(channel=channel, ts=thread_ts)
    return result.get("messages", [])


def format_thread_history(messages: list, bot_user_id: str) -> str:
    lines = []
    for msg in messages:
        user = msg.get("user", "unknown")
        text = msg.get("text", "").strip()
        if not text:
            continue
        role = "Assistant" if user == bot_user_id else "User"
        lines.append(f"{role}: {text}")
    return "\n".join(lines)


def parse_operator_from_text(text: str, valid_operators: set) -> str | None:
    m = re.match(r"^\[(\w+)\]", text.strip())
    if m and m.group(1).lower() in valid_operators:
        return m.group(1).lower()
    return None


def extract_operator_from_thread(messages: list, bot_user_id: str, valid_operators: set) -> str | None:
    for msg in reversed(messages):
        if msg.get("user") == bot_user_id:
            continue
        text = msg.get("text", "").split(">", 1)[-1].strip()
        op = parse_operator_from_text(text, valid_operators)
        if op:
            return op
    return None
