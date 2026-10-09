---
icon: lucide/globe
---

# Spotify Mirror

Music you play in Downtify shows up in your Spotify listening history —
Recently played, Friend Activity, the yearly wrap-up. It works through
**real Spotify playback**: when a track starts in Downtify, the same
track is started on **a Spotify Connect device on your own Premium
account**. This server ships with one — a silent one called **Downtify
Mirror** — but any of your Connect devices can be chosen instead.

Only real playback is recorded — nothing can inject listening history —
so the mirror is the real thing, as far as Spotify is concerned.

Admin-only: **Settings → Spotify Mirror**.

## Requirements

- **Spotify Premium** — the Web API playback endpoints only work for
  Premium accounts.
- **A Spotify Connect device reachable online.** The packaged one is
  described in [The Downtify Mirror device](#the-downtify-mirror-device);
  until it is set up, any running device (desktop Spotify, phone)
  works.
- **Your own Spotify developer app**:
  [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
  → *Create app*:
  - **Redirect URI**:
    `http://<your-server>:8000/integrations/spotify/callback` — the
    address the browser uses to reach Downtify (for example
    `http://100.89.246.67:8000/...`).
  - Which API: **Web API**.
  - Copy the `client_id` — the settings need it (PKCE doesn't use a
    client secret).

## Setup

In **Settings → Spotify Mirror**:

1. Switch **Enable Spotify Mirror** on.
2. **Spotify client id** — paste it, then save the page.
3. **Redirect URI** — must match what the Spotify app lists, exactly.
   The settings suggest the address this browser uses.
4. **Connect with Spotify** — the browser goes to Spotify's authorize
   page; approve, and you are sent back. Tokens are stored in the
   settings and the mirror switches on.
5. **Load devices** and pick the Spotify Connect device —
   **Downtify Mirror** is the usual choice.
6. **Test connection** — shows your Spotify username and the chosen
   device when everything is in place.

**Silent mirror** keeps the targeted device at volume 0: you listen in
Downtify; Spotify only gets to count.

The switch can stay on with just the client id — the mirror stays
inert until the account is connected **and** a device is chosen, so
the connect flow never gets rejected for not having either yet.

To stop mirroring, turn **Enable Spotify Mirror** off.

## How it behaves

A track's **start** is mirrored — the same signal
[scrobbling](scrobbling.md) uses — and the dedupe rule is the same:
one play command per player and song, so a scrub or a
pause/resume never sends a second one.

While the same track runs, the mirror follows the player:

* **Pause / resume** in Downtify pauses and resumes the mirrored
  device, once per transition.
* **Seeking** (the position jumps) moves the mirrored playback to the
  same spot — the web player flags a seek in its report.
* **Stopping** (the player goes away) pauses the mirror, so autoplay
  doesn't carry it on with recommendations.

Finding the track's Spotify id: Downtify stores it for everything it
downloaded (the track index registers a play for every download).
Anything else falls
back to a Spotify search by artist + title; when nothing matches, the
play is skipped.

Mirror failures are logged and skipped — lowering the volume to a gone
device, an offline device, a rate-limit hiccup — never does anything to
the playback you are hearing.

## The Downtify Mirror device

The server's `docker-compose.yml` can ship a `spotifyd` service — a
silent, always-on Spotify Connect client named **Downtify Mirror**. It
shows up in the device list once it is running and its credentials are
in place; that deployment step lives in
[Server setup](server.md#the-downtify-mirror-device). Until then, pointing the
mirror at any running device (desktop, phone) works the same way.

## Where the settings live

The block is `spotify_mirror` in `settings.json`:

```json
{
  "spotify_mirror": {
    "enabled": true,
    "client_id": "...",
    "redirect_uri": "http://your-server:8000/integrations/spotify/callback",
    "device_id": "downtify-mirror",
    "access_token": "...",
    "refresh_token": "...",
    "token_expires_at": 1793563800.0,
    "mirror_user": "you",
    "silent_on_target": true
  }
}
```

Saving it with only `client_id` (no tokens yet) is fine: the runtime
hooks mirror nothing until both a token and a device id exist.

## API

The browser flow (both are redirects the web page handles):

* `GET /integrations/spotify/authorize` — to Spotify's authorize page,
  using the saved `client_id` and redirect URI (PKCE).
* `GET /integrations/spotify/callback?code=&state=` — exchanges the
  code for tokens, saves them and sends the browser back to
  `/settings/apps?spotify=connected|error`.

The JSON endpoints (see the [API reference](../api-reference.md)):

* `GET /api/spotify-mirror/devices` — `{devices: [{id, name,
  is_active}]}`.
* `POST /api/spotify-mirror/test` — `{ok, username, device}` or
  `{ok: false, error: "auth_failed"|"device_missing"}`.
* `POST /api/spotify-mirror/mirror-now` — body `{track: {file, artist,
  title, ...}}`: starts that file's play on the device (an admin's
  test, outside the dedupe tracker).