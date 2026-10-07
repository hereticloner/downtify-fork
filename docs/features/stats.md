---
icon: lucide/bar-chart-3
---

# Stats

Stats is a read-only page that puts the size of your library and how much you use it in one place. It lives at `/library/stats`, in the Library area of the app (the **Library** item in the sidebar stays highlighted while you are there). There is nothing to configure — the page simply reads what Downtify already records.

## The numbers

Four cards sit across the top:

| Card | What it counts |
|------|----------------|
| **Tracks in library** | Audio files Downtify has indexed in the library |
| **Downloads (30 days)** | Download requests recorded in the last 30 days |
| **Plays** | Songs started in the [built-in player](player.md) or a paired app |
| **Liked** | Songs with a heart, from [Liked songs](liked-songs.md) |

The page also returns the number of playlists as part of the library numbers (see [API](#api)) even though it isn't shown as its own card.

## Downloads per day

Below the cards, **Downloads per day** lists each day that had a download, oldest first, with a bar scaled to the busiest day on the page and the day's count beside it. A day with no downloads simply isn't listed.

## Most played

**Most played** is the top ten songs by number of plays, most played first, each shown as its `Artist - Title` label and its count.

## Where the numbers come from

- **Tracks, playlists and likes** come from the library stores Downtify already keeps — the file index, the library playlist list and the liked-songs store.
- **Downloads and plays** come from the [activity log](../features/users.md) in `/data/downtify_activity.db`. The log keeps 90 days of entries, so every count here (including the all-time-looking ones) only covers the retained window.
- A **download** is one logged *request*: a playlist or album batch counts once, not once per track, because that is what the activity log records.
- A **play** is logged each time a song *starts* (a player reporting a new song), so replaying one song counts again. Top tracks group those plays by the label the log stored.
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

See the [API reference](../api-reference.md#stats).