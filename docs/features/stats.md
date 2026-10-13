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

## Where the numbers come from

- **Tracks, playlists and likes** come from the library stores Downtify already keeps — the file index, the library playlist list and the liked-songs store.
- **Downloads and plays** come from the [activity log](../features/users.md) in `/data/downtify_activity.db`. The log keeps 90 days of entries, so every count here (including the all-time-looking ones) only covers the retained window.
- A **download** is one logged *request*: a playlist or album batch counts once, not once per track, because that is what the activity log records.
- A **play** is logged each time a song *starts* (a player reporting a new song), so replaying one song counts again. Top tracks group those plays by the label the log stored.
- The **Spotify** panel is the one exception to the 90-day window: those rows are only ever added, never pruned, so the total keeps counting up for as long as the import is on.
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
    ]
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
| `spotify.recent` | Up to ten mirrored plays, newest first, each `{played_at, artist_name, track_name, album_name}` |
| `spotify.play_count` | Plays stored in the history table, all of them |

`spotify.recent` is `[]` and `spotify.play_count` is `0` until the history import has stored something.

See the [API reference](../api-reference.md#stats).