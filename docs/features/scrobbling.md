---
icon: lucide/music
---

# Scrobbling

Downtify can send the tracks you play to your [last.fm](https://www.last.fm)
profile, so your listening history follows you even when you play from your
own library instead of Spotify or YouTube Music.

Scrobbling is a Settings section for admins: **Settings → Scrobbling**.

## How it works

The player reports what it plays to Downtify (the same reports that power
Settings → Activity). When a track has played long enough to count, Downtify
sends it to last.fm:

* A track shorter than 30 seconds is never scrobbled.
* A track counts once it has played for **half its length or four minutes**,
  whichever comes first.
* Each track is scrobbled once per play, even if the player reports it many
  times.

Sending is best-effort: if last.fm is slow or down, the failure is logged and
playback continues unaffected.

## Setting up

1. Create a free last.fm API account at
   [last.fm/api/account/create](https://www.last.fm/api/account/create). You
   get an **API key** and an **API secret**.
2. In **Settings → Scrobbling**, switch **Enable scrobbling** on, then
   **last.fm** on.
3. Paste the **API key** and **API secret**.
4. Press **Connect last.fm**. Downtify asks last.fm for a request token and
   shows an **Authorize on last.fm** link — open it and approve.
5. Back in Downtify, press **Finish connecting**. Downtify trades the token
   for a session key and shows **Connected as {username}**.
6. Press **Test connection** to confirm the session works.

The session key is saved with your settings. To stop scrobbling, switch
**Enable scrobbling** off or press **Disconnect**.

## Settings

| Setting | What it does |
|---------|-------------|
| **Enable scrobbling** | Master switch for all scrobbling |
| **last.fm** | Scrobble to last.fm |
| **API key / API secret** | From your last.fm API account |
| **Update now playing** | Also tell last.fm what is playing before it is scrobbled |

## Where the settings live

The block is `scrobbling` in `settings.json`:

```json
{
  "scrobbling": {
    "enabled": true,
    "lastfm_enabled": true,
    "lastfm_api_key": "...",
    "lastfm_api_secret": "...",
    "lastfm_session_key": "...",
    "lastfm_username": "yourname",
    "scrobble_now_playing": true
  }
}
```

`POST /api/scrobbling/test` checks a session without saving it, and the
`POST /api/scrobbling/lastfm/auth/{start,finish}` pair runs the connect
flow. See the [API reference](../api-reference.md).