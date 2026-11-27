---
icon: lucide/bar-chart-3
---

# Stats

Stats is a read-only personal listening profile at `/library/stats`. It combines Downtify playback, imported Spotify plays and imported Last.fm scrobbles into one canonical history. The page uses the Technical Gazette visual system and does not show hour-of-day, weekday-pattern, clock or heatmap visualizations.

## Period and account scope

The **7 / 30 / 90 days** control changes only the selected-period summary, source split, known track time and Last.fm detail. The profile masthead, all-time totals, recent plays, top artists, top albums and top tracks always describe all stored canonical history; the four-week report always covers the same four UTC weeks regardless of the selected period.

The web page shows the signed-in account. An admin can request the server-wide view through the API with `scope=server`; the page keeps the personal view. Library size and likes remain server-wide.

## Profile masthead

The masthead shows the signed-in username, a square monogram, the first and last stored play dates, source precedence and the all-time most-played track. Empty history shows a localized empty state instead of invented dates or tracks.

## All-time profile

Four ruled cells summarize all stored canonical plays:

- **Total plays** — every canonical event for the selected account scope.
- **Artists** — distinct non-empty artist names.
- **Unique tracks** — distinct normalized artist/title keys.
- **Known albums** — distinct non-empty album names. “Known” is deliberate because some provider rows have no album.

The source ledger shows Downtify, Spotify and Last.fm canonical counts and percentages. These are winning sources after deduplication, not raw provider observation counts. Source precedence remains **Downtify → Spotify → Last.fm**.

## Recent plays

**Recent plays** lists the ten newest unified plays with a typographic monogram, track, artist, provider and localized time. The header carries the all-time canonical play total. The API can still return up to 400 recent rows.

## Top artists, albums and tracks

- **Top artists** ranks ten artists by canonical play count.
- **Top albums** shows eight album/artist pairs with counts and real library cover art when a matching album is available locally; initials appear only as the missing or broken-art fallback. The same album name from different artists remains separate.
- **Top tracks** ranks ten tracks with artist, known album and count. Structured `artist`, `title` and `album` fields accompany the existing `summary` label.

Every list has a truthful empty state and excludes blank names where the aggregate requires them.

## Listening report

The report shows four consecutive seven-day UTC buckets ending today, oldest first. Each row has a localized date range, exact canonical count and a flat ruled bar scaled to the busiest of the four weeks. It is a weekly count report, not an hourly or weekday-pattern analysis.

## Selected-period summary

The right-hand summary uses the selected 7, 30 or 90 UTC calendar days:

- canonical plays and source split;
- known track time with duration coverage.

Known track time sums stored track lengths. It is **not listening time**: a skipped track still contributes its full length, and Last.fm usually has no duration.

## Last.fm archive scope

For the selected period, the Last.fm block shows canonical plays whose linked scrobble was marked loved **at import**, canonical plays with a MusicBrainz ID, the number of imported Last.fm rows and the backfill state. The loved flag is a historical snapshot, not the account's current loved-track list. When backfill is running, the oldest imported date is shown; after an empty page is reached, the import is marked complete.

## Last.fm history

**Settings → Scrobbling → Import Last.fm history** brings the connected account's scrobbles into the unified Stats history. New plays are picked up every 15 minutes; older history is imported backwards in bounded pages and resumes after a restart or API failure. The currently-playing Last.fm entry is not counted as a play. Last.fm records usually carry artist/title metadata rather than a Spotify ID, so older rows remain visible even when they cannot be linked to a specific Downtify library ID.

A background fill-only pass copies missing album names from linked Last.fm rows and missing Spotify context/album values into canonical history. It never overwrites a value Downtify already knows.

## Where the numbers come from

- **Plays** come from one canonical `listening_events` table in `/data/downtify_activity.db`. It combines Downtify player starts, imported Spotify plays and imported Last.fm scrobbles. Replaying a song counts again; the all-time total is not pruned with the activity log.
- **Deduplication** uses normalized artist/title and a bounded time window. One real play seen through several providers produces one canonical row; a second observation from the same provider inside the window remains a separate play.
- **All-time profile** aggregates every stored canonical row for the selected account scope. Top albums group by album and artist so different artists' same-named albums do not merge.
- **Four-week report** groups canonical rows into four consecutive UTC calendar weeks ending today. Zero-play weeks remain visible.
- **Selected-period profile** reads canonical events from today and the preceding `days - 1` UTC calendar days. Source counts use the canonical winning source; unique tracks use `match_key`; unique artists/albums exclude empty names.
- **Known track time** sums positive `duration_ms` and reports how many period plays have a duration. It is track length, never measured listening time.
- **Last.fm detail** counts distinct linked canonical events with a truthy raw `loved` value or non-empty MBID. Imported-row count and backfill state are connection-level facts. Malformed raw JSON is ignored safely.
- **Historical enrichment** is a background, idempotent fill-only pass over already-linked raw Spotify/Last.fm rows. It repairs blank canonical album/context fields without changing source, identity, timestamp or play count, and never runs in a Stats GET.
- **Raw provider data** is kept separately: Spotify's original track object/ISRC/context and Last.fm's original scrobble object. These tables are included in metadata backups.
- **Measured listening** still uses only Downtify's position reports. Spotify and Last.fm do not fabricate seconds, completions or skips. The current Stats view does not display those measured cards.

## Retained API fields

The existing `heatmap`, `streak_days`, `best_day`, `patterns`, `day`, `pattern_detail`, `top_contexts`, download and Spotify-only response fields remain available for compatibility. The current Stats view does not render them.

## API

`GET /api/stats?days=30&scope=user` returns one object. `days` accepts `7`, `30` or `90`; anything else falls back to `30`. `scope=user` is the default and returns the signed-in account's activity. `scope=server` is admin-only and aggregates every account. Optional `date=YYYY-MM-DD` loads one exact UTC day into `playback.day`; invalid calendar dates return `400`. Optional `pattern=hour|weekday&bucket=N` loads exact bucket detail into `playback.pattern_detail`; both parameters are required together, hour is `0..23`, weekday is `0..6` (Sunday first), and invalid values return `400`.

The listening profile adds:

```json
{
  "playback": {
    "total": 4560,
    "top_tracks": [
      {
        "summary": "No Clear Mind - Big Thing",
        "artist": "No Clear Mind",
        "title": "Big Thing",
        "album": "Makena",
        "count": 115
      }
    ],
    "recent": [
      {
        "at": "2026-11-25T12:00:00Z",
        "date": "2026-11-25",
        "summary": "The Best Pessimist - Above the Fog (Pt.2)",
        "artist": "The Best Pessimist",
        "title": "Above the Fog (Pt.2)",
        "album": "",
        "context": "",
        "context_type": "",
        "source": "spotify"
      }
    ],
    "profile": {
      "first_at": "2026-10-07T12:18:00+00:00",
      "last_at": "2026-11-25T12:00:00Z",
      "unique": { "tracks": 1905, "artists": 788, "albums": 991 },
      "by_source": { "downtify": 226, "spotify": 2875, "lastfm": 1459 },
      "top_artists": [{ "artist": "No Clear Mind", "count": 732 }],
      "top_albums": [
        { "album": "Makena", "artist": "No Clear Mind", "count": 194 }
      ],
      "weeks": [
        { "start": "2026-10-31", "end": "2026-11-06", "count": 832 },
        { "start": "2026-11-07", "end": "2026-11-13", "count": 808 },
        { "start": "2026-11-14", "end": "2026-11-20", "count": 561 },
        { "start": "2026-11-21", "end": "2026-11-27", "count": 420 }
      ]
    }
  }
}
```

`profile` is all-time and account-scoped. `weeks` always contains four consecutive seven-day UTC buckets, oldest first, ending today. Empty history returns empty first/last timestamps, zero counts and empty top lists.

See the [API reference](../api-reference.md#stats) for the complete response.
