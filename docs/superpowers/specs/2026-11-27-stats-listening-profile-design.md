# Last.fm-style listening profile design

- **Date:** 2026-11-27
- **Status:** Implemented
- **Branch:** `feat/stats-profile`
- **Base:** `9b55e8d`

## Goal

Replace the Stats page's analytics-dashboard composition with a Last.fm-style personal listening profile in the existing Technical Gazette visual world. The page must not show hour-of-day, weekday-pattern, clock, heatmap or 24-hour-matrix visualizations.

## Approved composition

1. **Profile masthead:** signed-in username, square monogram, archive range and all-time top track. The 7/30/90-day control changes only the selected-period summary.
2. **Lifetime strip:** all-time canonical plays, unique artists, unique tracks and known albums, followed by the all-time canonical source ledger.
3. **Main profile body:**
   - Recent plays table: artwork/monogram, track, artist, source and time.
   - Top artists ledger: ten artists with canonical play counts.
   - Top albums grid: eight albums with artist and canonical play count.
   - Top tracks table: ten tracks with artist, album and canonical play count.
4. **Listening report column:** four consecutive seven-day UTC buckets ending today, selected-period summary/source split, Last.fm archive scope and known track time with explicit “not listening time” copy.
5. **Colophon:** counts come from stored/imported canonical plays; track lengths are not listening time; unmeasured seconds, completions and skips are not invented.

## Truth and compatibility constraints

- `listening_events` remains the only source of play counts. Raw provider rows are never summed.
- All-time profile values cover every stored canonical event for the selected account scope.
- Selected-period values continue to cover today and the preceding `days - 1` UTC days.
- Existing `/api/stats` fields and semantics remain available. New fields are additive.
- `top_tracks` and `recent` keep `summary` and all existing keys, and add structured `artist`, `title` and `album`.
- Source precedence remains Downtify → Spotify → Last.fm.
- Last.fm imported count/backfill remain connection-level stored facts.
- Known track time remains a sum of track lengths, never listened seconds.
- No fabricated system IDs, versions, storage, cache, codec, hardware, queue or sync telemetry.
- Preserve eight locales, light/dark tokens, square geometry, 2px rules, keyboard access and reduced-motion behavior.

## API additions

`GET /api/stats` adds:

```json
{
  "playback": {
    "top_tracks": [
      {
        "summary": "Artist - Title",
        "artist": "Artist",
        "title": "Title",
        "album": "Album",
        "count": 42
      }
    ],
    "recent": [
      {
        "at": "2026-11-25T21:15:00+00:00",
        "date": "2026-11-25",
        "summary": "Artist - Title",
        "artist": "Artist",
        "title": "Title",
        "album": "Album",
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
        { "start": "2026-10-31", "end": "2026-11-06", "count": 832 }
      ]
    }
  }
}
```

`profile.weeks` always contains four consecutive seven-day UTC buckets, oldest first, ending today. Empty history returns zero counts and empty first/last timestamps.

## Implementation surface

- `downtify/listening_history.py`: all-time profile aggregates, structured top/recent rows, four-week report.
- `downtify/stats.py`: activity-only fallback profile and additive response fields.
- `downtify/collections_api.py`: empty-activity response parity.
- `frontend/src/views/StatsView.vue`: replace dashboard sections with the approved profile; remove pattern/heatmap/download/Spotify-only panels from this view.
- `frontend/src/lib/statsProfile.js`: small pure display helpers for structured-row fallback and date/week labels.
- `frontend/src/i18n/locales/*.js`: new profile labels in all eight locales.
- Tests: backend profile contract, API shape, frontend profile rendering, no-pattern regression, locale parity and client SFC compilation.
- `docs/features/stats.md` and `docs/api-reference.md`: document the new page and additive fields.

## Acceptance

- Backend tests prove canonical counting, user scoping, all-time unique/source totals, top artists/albums, structured rows, four-week buckets and empty fallback.
- Frontend tests prove profile hierarchy, real counts, source labels, empty states, all eight locale keys and absence of pattern/heatmap sections.
- Full pytest, Vitest, Ruff, frontend build and docs build pass.
- Independent review finds no Critical/Important issue before merge/deploy.
- Desktop and mobile renders preserve the Technical Gazette identity without horizontal page overflow.

## Non-goals

- No new provider calls, tables or dependencies.
- No public sharing, OIDC, PostgreSQL, audio-provider or upstream merge work.
- No deletion of the existing pattern/day API fields; they remain for compatibility but are not rendered on this page.
