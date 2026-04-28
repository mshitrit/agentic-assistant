from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config.settings import SLACK_BOT_TOKEN, SLACK_APP_TOKEN
from agent.claude import ask_agent

app = App(token=SLACK_BOT_TOKEN)


@app.event("app_mention")
def handle_mention(event, say):
    question = event["text"]
    question = question.split(">", 1)[-1].strip()

    if not question:
        say("Please include a question after mentioning me.", thread_ts=event["ts"])
        return

    say("Analysing your question, please wait...", thread_ts=event["ts"])

    context = {"title": question}
    response = ask_agent(context)
    say(response, thread_ts=event["ts"])


if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
