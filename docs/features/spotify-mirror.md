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
7. Optional: with a track playing in this browser, **Mirror now** starts
   that same track on the device immediately — a full end-to-end check
   without waiting for the next play. It is a manual test, so it skips
   the dedupe tracker; the button is disabled while nothing is playing.

**Silent mirror** keeps the targeted device at volume 0: you listen in
Downtify; Spotify only gets to count.

The switch can stay on with just the client id — the mirror stays
inert until the account is connected **and** a device is chosen, so
the connect flow never gets rejected for not having either yet.

To stop mirroring, turn **Enable Spotify Mirror** off.

## Importing your listening history

The mirror only goes one way — Downtify → Spotify. The other direction
is a separate, **opt-in** switch: `import_recent` in the `spotify_mirror`
block. With it on, Downtify reads your Spotify listening history back
(`GET /v1/me/player/recently-played`, 50 entries per call, newest
first) roughly every 30 minutes and stores each play — timestamp, track,
artist, album, Spotify id and duration — in its own table,
`spotify_recently_played` in `downtify_activity.db`.

It is the same connection: same client id, same tokens, same
`ensure_token` refresh, no second sign-in. The stored rows are **history,
not library**: nothing is added to the catalog, no file is tagged, no
audio is touched or deleted.

Turn **Import listening history** on in **Settings → Spotify Mirror**,
next to **Silent mirror** (the switch is only clickable once the account
is connected). The same flag can be set in the settings block:

```json
{
  "spotify_mirror": {
    "enabled": true,
    "client_id": "...",
    "access_token": "...",
    "refresh_token": "...",
    "import_recent": true
  }
}
```

or over the API:

```bash
curl -b session.txt -X POST http://your-server:8000/api/settings/update \
  -H 'Content-Type: application/json' \
  -d '{"spotify_mirror": {"import_recent": true}}'
```

::: warning Reconnect once
The history import needs the `user-read-recently-played` scope, which the
connect flow started asking for with this feature. An account connected
earlier does not have it, and Spotify answers every fetch with `403`
until you connect again: clear `access_token` and `refresh_token` in the
`spotify_mirror` block, save, and use **Connect with Spotify** once more —
Spotify then asks for the extra scope. The save is refused up front with
that message if the import is switched on while the account has no
tokens.
:::

Whatever the import has stored shows up on the [Stats](stats.md#recently-played-on-spotify)
page as your last plays, with the total stored underneath.
:::

::: info A backstop, not a sampler
The endpoint answers a window that deliberately overlaps the previous
one, so a play that arrives twice is stored once (`played_at` is the
key). The sweep is slow on purpose: it catches what was missed, and it
only reaches as far back as Spotify hands out. A rate-limit (`429`) is
waited out up to a minute and retried on the next pass; a failed sweep
is logged and skipped, never fatal.
:::

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
* **Stopping** (the player goes away) pauses the mirror, so the device
  doesn't carry it on with recommendations.

The mirror device runs with `disable_autoplay: true` (`mirror/config.yml`).
Without it a track whose audio key Spotify refuses is *skipped*, and with
a playlist context that skip lands on the next track of that playlist —
the Spotify app then walks the playlist one second at a time while
Downtify keeps playing its own track. With autoplay off the device stops
on the failed track instead.

Finding the track's Spotify id: Downtify stores it for everything it
downloaded (the track index registers a play for every download).
Anything else falls
back to a Spotify search by artist + title; when nothing matches, the
play is skipped.

**Playing from a playlist.** When the track belongs to a playlist
Downtify knows about — a downloaded or synced playlist with its Spotify
id linked — the mirrored play carries that playlist as its
`context_uri`, starting at the exact track. Spotify then shows
*Playing from &lt;playlist&gt;* rather than a bare track, which is what
you would have seen had you played it there. A track in no linked
playlist still mirrors on its own, unchanged.

Mirror failures are logged and skipped — lowering the volume to a gone
device, an offline device, a rate-limit hiccup — never does anything to
the playback you are hearing. A failed attempt does **not** count as
mirrored: the same track is tried again on the next report instead of
being deduped away for the rest of the server's life.

## When a track doesn't show up

**Settings → Spotify Mirror** carries the answer on one panel: the
chosen Connect device and whether it is online right now, whether the
token still works, the last URI that went out, and the reason the last
attempt failed. It re-reads itself every 30 seconds while the section is
open. The panel is admin-only, like the section around it, and stays
empty when the server refuses the request.

The same answer is one call away for scripts — `GET
/api/spotify-mirror/status` returns whether the tokens still work,
whether the chosen Connect device is online right now, and what each
player last managed — the last URI that went out, or the reason the
last attempt failed (`no_uri`, `auth_failed`, `no_device`,
`play_failed: ...`).

```bash
curl -b session.txt http://your-server:8000/api/spotify-mirror/status
```

The last-play and last-error maps live in memory only (a restart clears
them) and are keyed `"<user_id>:<player>"` — the player id is the one
your player sends, `device:player`, e.g. `7:web:tab`.

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
    "silent_on_target": true,
    "import_recent": false
  }
}
```

Saving it with only `client_id` (no tokens yet) is fine: the runtime
hooks mirror nothing until both a token and a device id exist. The two
optional booleans are **Silent mirror** and
**Import listening history**; the history import only runs while
`enabled` is on too.

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
* `GET /api/spotify-mirror/status` — `{ok, device_id, device_name,
  device_online, token_valid, last_mirrors, last_errors}`: whether the
  mirror can play right now and what every player last managed.
* `POST /api/spotify-mirror/test` — `{ok, username, device}` or
  `{ok: false, error: "auth_failed"|"device_missing"}`.
* `POST /api/spotify-mirror/mirror-now` — body `{track: {file, artist,
  title, ...}}`: starts that file's play on the device (the
  **Mirror now** button; an admin's test, outside the dedupe tracker).