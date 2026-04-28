from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config.settings import SLACK_BOT_TOKEN, SLACK_APP_TOKEN
from agent.claude import ask_agent
from agent.prompts import AgentMode
from slack.client import get_bot_user_id, get_thread_history

app = App(token=SLACK_BOT_TOKEN)

_DISCLAIMER = (
    ":warning: *AI Disclaimer:* I am an AI assistant. "
    "Please do not share sensitive or confidential information. "
    "Analysing your question, please wait..."
)

_ERROR_MESSAGES = {
    "rate_limit": ":warning: I'm temporarily unavailable due to high demand. Please try again in a moment.",
    "api_error":  ":warning: I encountered an error and couldn't process your request. Please try again later.",
}


@app.event("app_mention")
def handle_mention(event, say, client):
    ts = event["ts"]
    thread_ts = event.get("thread_ts")
    channel = event["channel"]

    is_thread_reply = bool(thread_ts and thread_ts != ts)

    if is_thread_reply:
        bot_user_id = get_bot_user_id(client)
        thread_history = get_thread_history(client, channel, thread_ts, bot_user_id)
        context = {"title": thread_history}
        mode = AgentMode.SLACK_THREAD
        say("Analysing your question, please wait...", thread_ts=ts)
    else:
        question = event["text"].split(">", 1)[-1].strip()
        if not question:
            say("Please include a question after mentioning me.", thread_ts=ts)
            return
        context = {"title": question}
        mode = AgentMode.SLACK
        say(_DISCLAIMER, thread_ts=ts)

    result = ask_agent(context, mode=mode)
    if not result.ok:
        say(_ERROR_MESSAGES.get(result.error, _ERROR_MESSAGES["api_error"]), thread_ts=ts)
    else:
        say(result.response, thread_ts=ts)


if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
