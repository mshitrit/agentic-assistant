# Slack Bot Setup

This guide walks through creating and configuring the Slack app required to run `slack_bot_main.py`.

## 1. Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From Scratch**
2. Name it (e.g. `sbr-assistant`) and select your workspace → **Create App**

## 2. Enable Socket Mode

1. Go to **Settings → Socket Mode** → Toggle **Enable Socket Mode** → On
2. Click **Generate** → name the token (e.g. `socket-token`) → scope: `connections:write` only
3. Copy the `xapp-...` token — this is your `SLACK_APP_TOKEN`

## 3. Add Bot Token Scopes

Go to **OAuth & Permissions → Bot Token Scopes** and add:
- `app_mentions:read` — receive `@mention` events
- `chat:write` — post replies
- `channels:history` — read thread history in public channels
- `groups:history` — read thread history in private channels the bot is invited to
- `mpim:history` — read thread history in multi-person DMs (if the bot is added to a group DM)
- `im:history` — read thread history in 1:1 DMs with the bot

> Make sure these are under **Bot Token Scopes**, not User Token Scopes.

## 4. Subscribe to Events

1. Go to **Event Subscriptions** → Toggle **Enable Events** → On
2. Under **Subscribe to Bot Events** → Add `app_mention`
3. Save Changes

## 5. Install the App

1. Go to **OAuth & Permissions** → **Install to Workspace** → Allow
2. Copy the `xoxb-...` Bot Token — this is your `SLACK_BOT_TOKEN`

> Any time you change scopes or events, you must reinstall the app and update the token in `jira_config.txt`.

## 6. Configure Tokens

Add both tokens to `jira_config.txt`:
```
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
```

## 7. Invite the Bot to a Channel

In your Slack workspace, go to the channel and run:
```
/invite @sbr-assistant
```

## 8. Run the Bot

```bash
python3.11 slack_bot_main.py
```

Mention the bot in the channel to test:
```
@sbr-assistant how does detectOnlyMode work?
```
