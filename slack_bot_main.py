from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config.settings import SLACK_BOT_TOKEN, SLACK_APP_TOKEN
from agent.claude import ask_agent
from agent.prompts import AgentMode
from slack.client import get_bot_user_id, get_thread_history

app = App(token=SLACK_BOT_TOKEN)


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
    else:
        question = event["text"].split(">", 1)[-1].strip()
        if not question:
            say("Please include a question after mentioning me.", thread_ts=ts)
            return
        context = {"title": question}
        mode = AgentMode.SLACK

    say("Analysing your question, please wait...", thread_ts=ts)
    response = ask_agent(context, mode=mode)
    say(response, thread_ts=ts)


if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
