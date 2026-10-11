---
icon: lucide/refresh-cw
---

# Spotify Sync

When a playlist changes on Spotify — a track is added or removed — the
copy in your Downtify library stays as it was on the day it downloaded.
Spotify Sync keeps a downloaded playlist's **membership** in step with
Spotify on a schedule, so you do not have to paste the link and re-import
by hand.

It reuses the [Spotify Mirror](spotify-mirror.md) connection: the same
client id and tokens, the same `ensure_token` refresh. There is no second
sign-in and no new credentials.

Admin-only: **Settings → Spotify Mirror → Spotify Sync**.

## What it does — and what it does not

For every playlist the library knows by Spotify id, one sweep:

1. fetches the playlist's current track list from the Spotify Web API,
2. compares it to the last snapshot it stored,
3. **applies only the difference**:
   - tracks **added on Spotify** join the playlist — the
     [Queue](queue.md)'s missing-tracks flow pulls the audio, exactly
     like the playlist page's **Download missing** button;
   - tracks **removed on Spotify** leave the playlist: their catalog
     rows and M3U lines go, so the playlist stops listing them.

If nothing changed, the sweep does nothing at all — no M3U rewrite, no
catalog write, no request beyond the snapshot itself. A pure reorder is
not a change; the local playlist is a set, and shuffling it would only
be noise.

Audio files are **never deleted**. A track removed from one Spotify
playlist keeps its file on disk — it may belong to other playlists, and
deleting audio is not the sync's call. Only the playlist's membership
changes.

## Requirements

Spotify Sync rides the Spotify Mirror's OAuth connection, so the
[Mirror's requirements](spotify-mirror.md#requirements) apply: a Spotify
developer app and a connected account. Playlist reads use the same
tokens and add the `playlist-read-private` and
`playlist-read-collaborative` scopes, so **reconnect Spotify** after
upgrading if the account was connected before those scopes existed.

A playlist only syncs once it has been downloaded (or watched) so the
library has a Spotify id for it.

## Setup

In **Settings → Spotify Sync**:

1. Switch **Enable Spotify Sync** on. The interval field appears.
2. Pick a **Sync interval** — 15 minutes, 1 hour, 6 hours or 1 day (or
   type your own, from 5 minutes to 7 days).
3. Save the page.
4. **Sync now** runs one sweep immediately, ignoring the interval — a
   quick check that the connection works. It works even while the
   switch is off, so the account can be tested before committing to the
   automatic schedule.

The status line under the button shows the last sync time and how many
playlists are known, or tells you to connect Spotify first.

## How it behaves

The background loop wakes up every couple of minutes and syncs only the
playlists whose interval has elapsed — a quiet playlist is not fetched
on every wake-up. Leave the switch off (the default) and no request ever
goes out.

Failures are **logged and reported**, never silent:

- A token that cannot renew, or a playlist the API refuses, is written
  to the log and counted in the sweep's summary; the playlist keeps its
  old baseline, so the same diff is retried next time.
- The manual **Sync now** button turns a failure into a toast in the
  browser — "connect Spotify", "the sync finished with N error(s)" or
  "everything is already up to date".

A failed sweep never raises out of the loop and never touches the audio
or the rest of the library.

## Where the snapshot lives

The last-known track ids per playlist are one JSON file in the data
directory (`/data/downtify_spotify_sync.json`), next to the other
Downtify databases. It is a cache of what Spotify said last time, not
library data: losing it only means one extra baseline fetch.

The switch and interval live in the `spotify_sync` block of
`settings.json`:

```json
{
  "spotify_sync": {
    "enabled": true,
    "interval_minutes": 60
  }
}
```

## API

| Endpoint                     | What it does                                                                                      |
| ---------------------------- | ------------------------------------------------------------------------------------------------- |
| `GET /api/spotify-sync`      | Status: the switch, the interval, whether Spotify is connected, and each playlist's last snapshot |
| `POST /api/spotify-sync/run` | Run one sweep now, ignoring the interval and the switch. `400` when Spotify is not connected      |

See the [API reference](../api-reference.md#spotify-sync) for request
and response shapes.
