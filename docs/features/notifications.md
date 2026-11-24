---
icon: lucide/bell
---

# Notifications

Downtify can message you when something happens in the background, so you
do not have to keep the Queue page open to know a long sweep finished.
Channels are **Telegram**, **ntfy** and a generic **JSON webhook**. Events
include watch downloads, single/batch download results, library upgrades and
backups.

Notifications are a Settings section for admins: **Settings → Notifications**.

## Setting up a Telegram bot

You need a bot and the chat it should message. Both are free and take a
minute:

1. In Telegram, message [@BotFather](https://t.me/BotFather), send
   `/newbot` and follow the prompts. BotFather replies with a **token**
   that looks like `123456789:AA...`.
2. Start a chat with your new bot (or add it to a group) and send it any
   message. A bot can only message a chat that has talked to it first.
3. Get the **chat id**. The quickest way is to open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and read
   the `id` under `"chat"` — it is a number for a person, a negative
   number for a group.

## Turning it on

In **Settings → Notifications**:

1. Switch **Enable notifications** on.
2. Switch **Telegram** on.
3. Paste the **Bot token** and the **Chat id**.
4. Press **Send test message**. A message should arrive in the chat; if
   not, the token or chat id is wrong.
5. Choose the events each channel receives. Automatic download and upgrade
   notices start off; enable only what you want.

Notifications are off until you enter a token and a chat id: Downtify
refuses to save Telegram enabled without them.

## What gets sent

| Event | Message |
|-------|---------|
| A watch downloads new tracks | `Downtify downloaded 3 new tracks from "Road Trip"` |
| A download finishes or fails | Track title and artist, or a short failure reason |
| A batch finishes | One summary with downloaded/failed counts |
| A library upgrade starts/finishes | Queue size, then updated/failed/skipped counts |
| A backup completes | Backup filename |

Only actual downloads are announced. A track the watch found already on
disk (with *Overwrite existing files* off) is linked silently, not
downloaded, so it is not counted.

Sending is best-effort: if Telegram is slow or down, the failure is
logged and the download sweep finishes anyway. The swap happens off the
download loop, so a stuck notification never holds up a download.

## ntfy and webhooks

**ntfy** needs the full topic URL, for example `https://ntfy.sh/my-topic`.
A protected topic also needs its access token. **Webhook** POSTs JSON with
`event`, `message` and `payload`; an optional token is sent as
`Authorization: Bearer …`. Only HTTP and HTTPS endpoints are accepted.

## Telegram commands

When Telegram is enabled, the bot long-polls for commands. It answers only
the configured chat id, and only accepts `/help`, `/status` and `/queue`.
These commands are read-only; there are no pause, resume or delete commands.

## Where the settings live

Public switches and event selections live in the `notifications` block of
`settings.json`. Credentials live separately in `notifications.json`, written
atomically with mode `0600`. API responses expose only `<field>_set` flags:

```json
{
  "notifications": {
    "enabled": true,
    "events": ["watch.downloaded"],
    "channels": {
      "telegram": {
        "enabled": true,
        "events": ["watch.downloaded"],
        "bot_token_set": true,
        "chat_id_set": true
      }
    }
  }
}
```

Old inline Telegram credentials are moved to `notifications.json` on first
start. Leaving a secret field blank in Settings keeps the saved value.

`POST /api/notifications/test?channel=telegram|ntfy|webhook` tests one channel.
The body may be `{ "channel": "ntfy", "config": { ... } }`; typed secrets
override saved ones. See the [API reference](../api-reference.md).
