---
icon: lucide/bar-chart-3
---

# Stats

Stats is a read-only personal listening profile at `/library/stats`. It counts **Downtify playback + Last.fm scrobbles only**. Spotify plays are still imported into the canonical history and kept as raw archive data, but Spotify-only plays are excluded from every Stats aggregate and detail. The page uses the Technical Gazette visual system and does not show hour-of-day, weekday-pattern, clock or heatmap visualizations.

## Period and account scope

The **7 / 30 / 90 days** control changes only the selected-period summary, source split, known track time and Last.fm detail. The profile masthead, all-time totals, recent plays, top artists, top albums and top tracks always describe all stored canonical history; the four-week report always covers the same four UTC weeks regardless of the selected period.

The web page shows the signed-in account. An admin can request the server-wide view through the API with `scope=server`; the page keeps the personal view. Library size and likes remain server-wide.

## Profile masthead

The masthead shows the signed-in username, a square monogram, the first and last stored play dates, the Stats source order (Downtify → Last.fm) and the all-time most-played track. Empty history shows a localized empty state instead of invented dates or tracks.

## All-time profile

Four ruled cells summarize all stored canonical plays:

- **Total plays** — every canonical event for the selected account scope.
- **Artists** — distinct non-empty artist names.
- **Unique tracks** — distinct normalized artist/title keys.
- **Known albums** — distinct non-empty album names. “Known” is deliberate because some provider rows have no album.

The source ledger shows only the Downtify and Last.fm canonical counts and percentages: these are winning sources after deduplication, not raw provider observation counts. Canonical reconciliation uses **Downtify → Last.fm → Spotify** precedence, so a play known to Downtify or Last.fm keeps that metadata while Spotify wins only when neither does. Spotify-only winners are not Stats sources, and `by_source.spotify` stays `0` for API compatibility.

## Recent plays

**Recent plays** lists the ten newest Downtify/Last.fm plays with a typographic monogram, track, artist, provider badge and localized time. Legacy Spotify rows in an older payload are ignored. The header carries the filtered all-time Stats total; the API can still return up to 400 recent rows.

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

- **Plays** come from one canonical `listening_events` table in `/data/downtify_activity.db`. It stores Downtify player starts, imported Spotify plays and imported Last.fm scrobbles, but Stats reads only Downtify and Last.fm winners. Replaying a song counts again; the all-time total is not pruned with the activity log.
- **Deduplication** uses normalized artist/title and a bounded time window. One real play seen through several providers produces one canonical row; a second observation from the same provider inside the window remains a separate play.
- **Reconciliation** resolves the canonical winner in Downtify → Last.fm → Spotify order without changing event identity or provider links. A legacy Spotify winner linked to a Last.fm scrobble is upgraded to Last.fm metadata on bootstrap.
- **Source filter** applies to all-time and period profiles, recent/top lists, track time, day detail and pattern detail: Spotify-only canonical rows are excluded everywhere in Stats, while the legacy `spotify` fields and raw rows are left intact.
- **Startup catch-up** runs one bounded pass of each provider's importer before the periodic history loops start, so new Downtify/Last.fm pages and scrobbles appear without waiting for the next interval; a failing provider does not fail startup.
- **All-time profile** aggregates every stored Downtify/Last.fm canonical row for the selected account scope. Top albums group by album and artist so different artists' same-named albums do not merge.
- **Four-week report** groups the filtered canonical rows into four consecutive UTC calendar weeks ending today. Zero-play weeks remain visible.
- **Selected-period profile** reads Downtify/Last.fm canonical events from today and the preceding `days - 1` UTC calendar days. Source counts use the canonical winning source; unique tracks use `match_key`; unique artists/albums exclude empty names.
- **Known track time** sums positive `duration_ms` and reports how many period plays have a duration. It is track length, never measured listening time.
- **Last.fm detail** counts distinct linked canonical events with a truthy raw `loved` value or non-empty MBID. Imported-row count and backfill state are connection-level facts. Malformed raw JSON is ignored safely.
- **Historical enrichment** is a background, idempotent fill-only pass over already-linked raw Spotify/Last.fm rows. It repairs blank canonical album/context fields without changing source, identity, timestamp or play count, and never runs in a Stats GET.
- **Raw provider data** is kept separately: Spotify's original track object/ISRC/context and Last.fm's original scrobble object. These tables are included in metadata backups; being stored does not make Spotify a Stats source.
- **Measured listening** still uses only Downtify's position reports. Spotify and Last.fm do not fabricate seconds, completions or skips. The current Stats view does not display those measured cards.

## Retained API fields

The existing `heatmap`, `streak_days`, `best_day`, `patterns`, `day`, `pattern_detail`, `top_contexts`, download and top-level `spotify` response fields remain available for compatibility. The top-level Spotify archive and legacy `by_source.spotify` are not Stats sources (the latter stays `0`); the current Stats view does not render them.

## API

`GET /api/stats?days=30&scope=user` returns one object. `days` accepts `7`, `30` or `90`; anything else falls back to `30`. `scope=user` is the default and returns the signed-in account's activity. `scope=server` is admin-only and aggregates every account. Optional `date=YYYY-MM-DD` loads one exact UTC day into `playback.day`; invalid calendar dates return `400`. Optional `pattern=hour|weekday&bucket=N` loads exact bucket detail into `playback.pattern_detail`; both parameters are required together, hour is `0..23`, weekday is `0..6` (Sunday first), and invalid values return `400`.

The listening profile adds this illustrative two-source payload (example counts, not a live measurement):

```json
{
  "playback": {
    "total": 3,
    "top_tracks": [
      {
        "summary": "No Clear Mind - Big Thing",
        "artist": "No Clear Mind",
        "title": "Big Thing",
        "album": "Makena",
        "count": 2
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
        "source": "lastfm"
      }
    ],
    "profile": {
      "first_at": "2026-10-07T12:18:00+00:00",
      "last_at": "2026-11-25T12:00:00Z",
      "unique": { "tracks": 3, "artists": 3, "albums": 1 },
      "by_source": { "downtify": 1, "spotify": 0, "lastfm": 2 },
      "top_artists": [{ "artist": "No Clear Mind", "count": 2 }],
      "top_albums": [
        { "album": "Makena", "artist": "No Clear Mind", "count": 2 }
      ],
      "weeks": [
        { "start": "2026-10-31", "end": "2026-11-06", "count": 0 },
        { "start": "2026-11-07", "end": "2026-11-13", "count": 0 },
        { "start": "2026-11-14", "end": "2026-11-20", "count": 1 },
        { "start": "2026-11-21", "end": "2026-11-27", "count": 2 }
      ]
    }
  }
}
```

`profile` is all-time and account-scoped. `weeks` always contains four consecutive seven-day UTC buckets, oldest first, ending today. Empty history returns empty first/last timestamps, zero counts and empty top lists.

See the [API reference](../api-reference.md#stats) for the complete response.
