---
icon: lucide/bar-chart-3
---

# Stats

Stats is a read-only page that puts the size of your library and how much you use it in one place. It lives at `/library/stats`, in the Library area of the app (the **Library** item in the sidebar stays highlighted while you are there). There is nothing to configure — the page simply reads what Downtify already records.

## The numbers

Six cards sit across the top:

| Card | What it counts |
|------|----------------|
| **Tracks in library** | Audio files Downtify has indexed in the library |
| **Playlists in library** | Playlists in the library |
| **Downloads (30 days)** | Download requests recorded in the last 30 days |
| **Downloads (all time)** | Download requests in the whole retained activity log |
| **Plays** | Songs started in the [built-in player](player.md) or a paired app |
| **Liked** | Songs with a heart, from [Liked songs](liked-songs.md) |

The two download cards come from the same log: one counts the retained window, the other everything still in it (see [Where the numbers come from](#where-the-numbers-come-from)).

## Downloads per day

Below the cards, **Downloads per day** lists each day that had a download, oldest first, with a bar scaled to the busiest day on the page and the day's count beside it. A day with no downloads simply isn't listed.

## Most played

**Most played** is the top ten songs by number of plays, most played first, each shown as its `Artist - Title` label and its count.

## Recently played on Spotify

**Recently played on Spotify** lists your last plays that Downtify mirrored out of Spotify, newest first — when each happened and its `Artist - Title` label — with the total number of stored plays underneath. It stays empty until you turn the history import on (**Settings → Spotify Mirror → Import listening history**, see [Spotify Mirror](spotify-mirror.md#importing-your-listening-history)); the plays are read from the same store the import fills, so nothing is fetched when the page loads.

## Listening activity

**Listening activity** is a GitHub-style heatmap of the last 52 weeks: one column per week, one cell per day, oldest week on the left. A day with no play is the empty grey; the more you played, the stronger the green. The shading is scaled to your busiest day of that window, so even a quiet month keeps its shape. Hovering a cell shows the date and how many songs were played on it.

Underneath the grid are two numbers:

- **Day streak** — how many days in a row you played something. A day that hasn't finished doesn't break it: until midnight is over, yesterday's run still counts. Nothing played today *and* yesterday means zero.
- **Busiest day** — the day of that window with the most plays, with the date and the count.

Both come from the same [activity log](../features/users.md) as the other panels, and are server-wide: everyone using the same server contributes to the same grid.

## Where the numbers come from

- **Tracks, playlists and likes** come from the library stores Downtify already keeps — the file index, the library playlist list and the liked-songs store.
- **Downloads and plays** come from the [activity log](../features/users.md) in `/data/downtify_activity.db`. The log keeps a year of entries, so every count here (including the all-time-looking ones) only covers the retained window.
- A **download** is one logged *request*: a playlist or album batch counts once, not once per track, because that is what the activity log records.
- A **play** is logged each time a song *starts* (a player reporting a new song), so replaying one song counts again. Top tracks group those plays by the label the log stored. The heatmap counts those same plays per day, one entry per day of the window — including the days with none, which come back as `0`.
- The **Spotify** panel is the one exception to the retained window: those rows are only ever added, never pruned, so the total keeps counting up for as long as the import is on.
- The counts are **server-wide**, not per account — everyone using the same server contributes to the same numbers.

## API

`GET /api/stats` returns one object:

```json
{
  "library": { "tracks": 812, "playlists": 44, "likes": 96 },
  "downloads": {
    "total": 310,
    "last_30_days": 27,
    "per_day": [
      { "date": "2026-09-29", "count": 3 },
      { "date": "2026-09-30", "count": 1 }
    ]
  },
  "playback": {
    "total": 1543,
    "top_tracks": [
      { "summary": "The Night Owls - Do I Still Recall", "count": 42 }
    ],
    "heatmap": [
      { "date": "2026-09-29", "count": 2 },
      { "date": "2026-09-30", "count": 0 }
    ],
    "streak_days": 4,
    "best_day": { "date": "2026-10-10", "count": 31 }
  },
  "spotify": {
    "recent": [
      {
        "played_at": "2026-10-12T21:15:00+00:00",
        "artist_name": "The Night Owls",
        "track_name": "Do I Still Recall",
        "album_name": "Night Owls"
      }
    ],
    "play_count": 1284
  }
}
```

| Field | Meaning |
|-------|---------|
| `library.tracks` | Files in the library index |
| `library.playlists` | Playlists in the library |
| `library.likes` | Liked songs |
| `downloads.total` | Download requests in the activity log |
| `downloads.last_30_days` | Those within the last 30 days |
| `downloads.per_day` | `{date, count}` for each day with a download, oldest first |
| `playback.total` | Plays in the activity log |
| `playback.top_tracks` | Up to ten `{summary, count}`, most played first |
| `playback.heatmap` | `{date, count}` for every day of the retained window (364 days), oldest first — days without a play are `0` |
| `playback.streak_days` | Days in a row with a play; a day still to come doesn't break it |
| `playback.best_day` | `{date, count}` for the busiest day of the window, or `{"date": "", "count": 0}` when nothing was played |
| `spotify.recent` | Up to ten mirrored plays, newest first, each `{played_at, artist_name, track_name, album_name}` |
| `spotify.play_count` | Plays stored in the history table, all of them |

`spotify.recent` is `[]` and `spotify.play_count` is `0` until the history import has stored something.

See the [API reference](../api-reference.md#stats).