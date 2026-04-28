def get_bot_user_id(client) -> str:
    return client.auth_test()["user_id"]


def get_thread_history(client, channel: str, thread_ts: str, bot_user_id: str) -> str:
    result = client.conversations_replies(channel=channel, ts=thread_ts)
    messages = result.get("messages", [])
    lines = []
    for msg in messages:
        user = msg.get("user", "unknown")
        text = msg.get("text", "").strip()
        if not text:
            continue
        role = "Assistant" if user == bot_user_id else "User"
        lines.append(f"{role}: {text}")
    return "\n".join(lines)
