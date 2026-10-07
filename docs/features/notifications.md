---
icon: lucide/bell
---

# Notifications

Downtify can message you when something happens in the background, so you
do not have to keep the Queue page open to know a long sweep finished.
Today the only channel is **Telegram**, and the event is a
[Playlist Monitor](playlist-monitor.md) watch that downloaded new tracks.

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
5. Leave **New tracks from a watch** on to be told when a playlist or
   artist watch downloads new tracks.

Notifications are off until you enter a token and a chat id: Downtify
refuses to save Telegram enabled without them.

## What gets sent

| Event | Message |
|-------|---------|
| A watch downloads new tracks | `Downtify downloaded 3 new tracks from "Road Trip"` |

Only actual downloads are announced. A track the watch found already on
disk (with *Overwrite existing files* off) is linked silently, not
downloaded, so it is not counted.

Sending is best-effort: if Telegram is slow or down, the failure is
logged and the download sweep finishes anyway. The swap happens off the
download loop, so a stuck notification never holds up a download.

## Where the settings live

The block is `notifications` in `settings.json`:

```json
{
  "notifications": {
    "enabled": true,
    "telegram_enabled": true,
    "telegram_bot_token": "123456789:AA...",
    "telegram_chat_id": "987654321",
    "notify_watch_downloads": true
  }
}
```

`POST /api/notifications/test` sends a test message from the values you
send it, whether or not they are saved — the same call the **Send test
message** button makes. See the [API reference](../api-reference.md).