from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config.settings import SLACK_BOT_TOKEN, SLACK_APP_TOKEN, OPERATORS, SLACK_OPERATOR_TAGS
from agent.claude import ask_agent
from agent.prompts import AgentMode
from slack.client import (
    get_bot_user_id,
    fetch_thread_messages,
    format_thread_history,
    parse_operator_from_text,
    extract_operator_from_thread,
)
from telemetry.metrics import slack_metrics

app = App(token=SLACK_BOT_TOKEN)

_ERROR_MESSAGES = {
    "rate_limit": ":warning: I'm temporarily unavailable due to high demand. Please try again in a moment.",
    "api_error":  ":warning: I encountered an error and couldn't process your request. Please try again later.",
}


def _operator_error_message() -> str:
    valid_list = ", ".join(f"[{k.upper()}]" for k in sorted(SLACK_OPERATOR_TAGS))
    tags = sorted(SLACK_OPERATOR_TAGS)
    ex_a, ex_b = (tags[0], tags[-1]) if len(tags) >= 2 else (tags[0], tags[0]) if tags else ("sbr", "sbr")
    return (
        f":warning: Please prefix your question with an operator tag. Valid options: {valid_list}\n"
        f"Examples: `[{ex_a.upper()}] your question`  ·  `[{ex_b.upper()}] your question`"
    )


def _operator_not_configured_message(operator: str) -> str:
    u = operator.upper()
    return (
        f":warning: Operator `[{u}]` is not enabled in `config/config.txt`. "
        f"Add `OPERATOR_{u}_COMPONENTS=...` (and optional `OPERATOR_{u}_REPO_PATH`). "
        f"See `config/config.template.txt` for examples."
    )


def _is_slack_operator_configured(operator: str) -> bool:
    return bool((OPERATORS.get(operator) or {}).get("components"))


def _resolve_op_name(operator: str) -> str:
    return OPERATORS[operator]["components"][0]


@app.event("app_mention")
def handle_mention(event, say, client):
    ts = event["ts"]
    thread_ts = event.get("thread_ts")
    channel = event["channel"]

    is_thread_reply = bool(thread_ts and thread_ts != ts)

    if is_thread_reply:
        bot_user_id = get_bot_user_id(client)
        messages = fetch_thread_messages(client, channel, thread_ts)
        operator = extract_operator_from_thread(messages, bot_user_id, SLACK_OPERATOR_TAGS)
        if operator is None:
            say(":warning: Could not determine operator context. Please start a new thread with an operator tag.", thread_ts=ts)
            return
        if not _is_slack_operator_configured(operator):
            say(_operator_not_configured_message(operator), thread_ts=ts)
            return
        op_name = _resolve_op_name(operator)
        thread_history = format_thread_history(messages, bot_user_id)
        context = {"title": thread_history}
        mode = AgentMode.SLACK_THREAD
        slack_metrics.inc_followups()
        say(f"Analysing your follow-up question about *{op_name}*, please wait...", thread_ts=ts)
    else:
        question = event["text"].split(">", 1)[-1].strip()
        if not question:
            say("Please include a question after mentioning me.", thread_ts=ts)
            return
        operator = parse_operator_from_text(question, SLACK_OPERATOR_TAGS)
        if operator is None:
            say(_operator_error_message(), thread_ts=ts)
            return
        if not _is_slack_operator_configured(operator):
            say(_operator_not_configured_message(operator), thread_ts=ts)
            return
        op_name = _resolve_op_name(operator)
        context = {"title": question}
        mode = AgentMode.SLACK
        slack_metrics.inc_threads_started()
        say(
            f":warning: *AI Disclaimer:* I am an AI assistant. "
            f"Please do not share sensitive or confidential information. "
            f"Analysing your question about *{op_name}*, please wait...",
            thread_ts=ts
        )

    result = ask_agent(context, mode=mode, operator=operator, op_name=op_name)
    if not result.ok:
        slack_metrics.inc_errors()
        say(_ERROR_MESSAGES.get(result.error, _ERROR_MESSAGES["api_error"]), thread_ts=ts)
    else:
        slack_metrics.inc_success()
        say(result.response, thread_ts=ts)


if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
