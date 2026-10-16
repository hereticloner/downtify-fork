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

**Listening activity** is a GitHub-style heatmap of the last 52 weeks: one column per week, one cell per day, oldest week on the left. A day with no play is the empty grey; the more you played, the stronger the green. The shading is scaled to your busiest day of that window, so even a quiet month keeps its shape.

The cells arrive one after another rather than all at once, each column a moment behind the last, and each cell grows under the cursor and when the keyboard reaches it.

- **Hovering** (or focusing) a cell shows the full date and how many songs were played on it.
- **Clicking** a cell — or pressing it with the keyboard — opens **Recent plays** filtered to that day, and rings the cell so the choice stays visible once the cursor moves away. Clicking the same cell again, or **All days**, clears it.

Underneath the grid are two numbers:

- **Day streak** — how many days in a row you played something. A day that hasn't finished doesn't break it: until midnight is over, yesterday's run still counts. Nothing played today *and* yesterday means zero.
- **Busiest day** — the day of that window with the most plays, with the date and the count.

Both come from the same [activity log](../features/users.md) as the other panels, and are server-wide: everyone using the same server contributes to the same grid.

## Recent plays

**Recent plays** lists what you actually played, newest first: the time, the `Artist - Title` label, and — when the player knew it — **the queue it came from** as a small tag. That is the playlist, album or artist you pressed play on, so "what did I listen to" answers with a source rather than a bare title. Without a day picked in the heatmap it lists your newest plays; with one, only that day's.

Only plays from after this shipped carry the tag. A player that reports no queue (an older app, a bare library play) is simply listed without one.

## Most played from

**Most played from** groups the same plays by the queue that served them, most played first — the playlists you actually start, rather than the songs inside them.

## Last 30 days

**Last 30 days** draws the tail of the heatmap as a line, scaled to its own busiest day so a quiet week still reads as a shape. Under it: how many plays those 30 days hold, how many of them you listened on a day at all, and your average per listening day.

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
    "best_day": { "date": "2026-10-10", "count": 31 },
    "recent": [
      {
        "at": "2026-10-12T21:15:00+00:00",
        "date": "2026-10-12",
        "summary": "The Night Owls - Do I Still Recall",
        "context": "Chill Deploy",
        "context_type": "playlist"
      }
    ],
    "top_contexts": [{ "context": "Chill Deploy", "count": 128 }]
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
| `playback.recent` | Up to 400 of your newest plays, newest first, each `{at, date, summary, context, context_type}` — `context` is the queue it was served from, empty when the player reported none |
| `playback.top_contexts` | Up to ten `{context, count}`, most played first; plays without a queue are left out |
| `spotify.recent` | Up to ten mirrored plays, newest first, each `{played_at, artist_name, track_name, album_name}` |
| `spotify.play_count` | Plays stored in the history table, all of them |

`spotify.recent` is `[]` and `spotify.play_count` is `0` until the history import has stored something.

See the [API reference](../api-reference.md#stats).