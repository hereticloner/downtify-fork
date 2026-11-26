# Stats detail + interactive listening heatmap

- **Date:** 2026-11-26
- **Status:** Approved — deep analytics scope; implementation authorized
- **Branch:** `feat/personal-server-program`
- **Base:** `3076ad8`

## Goal

Make Stats more useful with truthful Spotify/Last.fm-derived detail, and fix the GitHub-style listening heatmap so it is reliable with mouse, keyboard and touch.

The approved scope is the **deep analytics package**: period/source/unique/duration aggregates, UTC listening patterns, Last.fm detail and backfill state, historical metadata enrichment, plus all reproduced heatmap correctness and interaction defects. No new provider calls, tables or dependencies.

## Evidence and constraints

- Spotify Recently Played supplies `played_at`, track `duration_ms` and context, but **not listened seconds**.
- Last.fm recent-track scrobbles supply timestamps, album/MBID and a per-scrobble `loved` snapshot, but **not listened duration**.
- Only Downtify position reports can populate `playback.measured.seconds`, completions and skips.
- The canonical `listening_events` table is the only source for play counts. Raw provider rows must never be summed: one real play can have several linked observations.
- The live audit found 4,560 canonical plays from 6,972 raw observations. A duration sum is therefore track length, not listening time.
- Last.fm backfill is still partial; every number must describe **stored/imported history**, not claim a provider's complete lifetime total.
- New Spotify and Last.fm links already propagate context/album. Older canonical rows linked before that behavior need an idempotent fill-only enrichment pass.
- Reproduced heatmap defects: tooltip clears over internal gaps; hover stores a stale cell snapshot; 364 tab stops; English-only play count; selected outline is overridden on hover; selected-day details are filtered from a 400-row page and can be empty; backend “busiest day” chooses the newest active day rather than the maximum.

## User experience

### 1. Truthful time and listening profile

Keep the existing measured card, but label it **Measured listening** and make clear it is Downtify-only. Add a compact **Listening profile** section for the selected 7 / 30 / 90-day UTC window:

- **Plays in period** — canonical play total for the window.
- **Source split** — Downtify / Spotify / Last.fm counts and proportional bars. These are canonical winning sources after dedupe, not raw observation counts.
- **Unique tracks / artists / known albums** — distinct normalized track keys and non-empty names in the same window.
- **Known track time** — sum of available `duration_ms`, with `N of M plays have duration`. It is explicitly labelled as track time, never listening time.

The existing all-time unified play count remains unchanged and continues to mean all stored canonical plays. The Spotify panel and its raw stored-play count remain unchanged.

### 2. UTC listening patterns

Add two compact distributions for the same selected window:

- **Hour of day (UTC)** — 24 bars, `00` through `23`.
- **Day of week (UTC)** — seven bars, Sunday first.

They are labelled UTC because the server stores UTC timestamps and has no reliable per-user timezone. No local-time claim is made.

### 3. Last.fm detail

Within the profile, show:

- Canonical plays with a linked Last.fm scrobble marked loved at import.
- Canonical plays with a MusicBrainz ID.
- Import state: no history imported, import in progress with the oldest imported timestamp, or backfill complete.

The loved flag is a historical snapshot, not the account's current loved-track list. Backfill state is connection-level because Last.fm is a server setting; loved/MBID counts remain account/server scoped like other playback aggregates.

### 4. Historical metadata enrichment

Add a background, idempotent enrichment pass for already-linked raw rows:

- Fill blank canonical album from linked Spotify or Last.fm raw metadata.
- Fill blank canonical context/context type from linked Spotify context.
- Never overwrite a non-empty canonical value.
- Never change source, identity, timestamp, match key or play count.

New links already carry these fields. The pass repairs historical rows and picks up Spotify raw payloads enriched after their original link. It runs in the existing background bootstrap/sweep path, not in a Stats GET.

### 5. Reliable heatmap interaction

- Hover or focus shows a localized date and localized play count.
- Moving across the 2px gaps inside the grid does not hide the tooltip.
- If data refreshes while a day is hovered, the tooltip reads the new count for that date.
- The grid has one tab stop. Arrow Left/Right move one day; Arrow Up/Down move seven days; Home/End jump to the first/last day; Enter/Space select.
- The selected day keeps its accent ring on hover and focus.
- The tooltip has `role="tooltip"`; the active cell references it with `aria-describedby`.
- Fine pointers keep the compact 8px painted cells. Coarse pointers get 24px button targets with the same 8px painted squares and horizontal scrolling.
- Reduced motion still disables the tooltip transition.

### 6. Complete selected-day details

Clicking a heatmap day requests that exact UTC day from the server instead of filtering the 400-row recent page. The response carries the exact day total and up to 400 plays for that day. If truncated, the panel says so.

The day request runs in the background: the heatmap does not unmount, selection and keyboard focus remain visible, and period changes keep the selected day. A failed day request keeps the page intact and shows an inline retry. Rapid selections cannot apply an older response over a newer one.

### 7. Correct busiest day

`playback.best_day` becomes the maximum-count day in the heatmap window. Ties keep the earliest maximum, matching the existing frontend helper. Empty windows still return `{"date":"","count":0}`.

## API contract

`GET /api/stats` keeps all existing fields and semantics. Add one optional query parameter:

- `date=YYYY-MM-DD` — exact UTC day to load for the Recent plays panel. Invalid dates return `400`. Omitting it returns an empty `playback.day` object.

Additive `playback` fields:

```json
{
  "period": {
    "days": 30,
    "total": 123,
    "by_source": { "downtify": 12, "spotify": 100, "lastfm": 11 }
  },
  "unique": {
    "tracks": 80,
    "artists": 31,
    "albums": 52
  },
  "track_time": {
    "seconds": 73200,
    "plays_with_duration": 120,
    "plays_without_duration": 3
  },
  "patterns": {
    "by_hour": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "by_weekday": [0, 0, 0, 0, 0, 0, 0]
  },
  "day": {
    "date": "2026-11-20",
    "total": 40,
    "plays": [
      {
        "at": "2026-11-20T21:15:00+00:00",
        "date": "2026-11-20",
        "summary": "Artist - Title",
        "context": "",
        "context_type": "",
        "source": "spotify"
      }
    ]
  },
  "lastfm": {
    "loved_plays": 4,
    "mbid_plays": 100,
    "imported_plays": 3800,
    "backfill": {
      "done": false,
      "oldest_at": "2026-10-11T21:46:08Z",
      "newest_at": "2026-11-25T21:00:00Z"
    }
  }
}
```

Semantics:

- `period`, `unique`, `track_time`, `patterns`, `lastfm.loved_plays` and `lastfm.mbid_plays` cover the selected UTC calendar window: today and the preceding `days - 1` days.
- `period.by_source` counts canonical events only and always includes all three source keys.
- `unique.tracks` is `COUNT(DISTINCT match_key)`; artists and albums exclude empty strings. Albums remain “known albums” because some provider metadata is absent.
- `track_time.seconds` is `SUM(duration_ms) / 1000` for positive durations. It is not listened time.
- `patterns.by_hour` has 24 integer counts, UTC hour 0–23. `patterns.by_weekday` has seven integer counts, Sunday first (`0`) through Saturday (`6`).
- `lastfm.loved_plays` counts distinct canonical events with a linked Last.fm row whose raw `loved` value is truthy at import. `lastfm.mbid_plays` counts distinct canonical events with a non-empty MBID.
- `lastfm.imported_plays` and `lastfm.backfill` are connection-level stored import facts, not selected-period metrics.
- `day.total` is the exact canonical count for the requested date and scope. `day.plays` is capped at 400, newest first.
- The `activity is None` fallback returns the same additive keys with empty/zero values.

## Implementation surface

### Backend

- `downtify/listening_history.py`
  - Extend `ListeningStore.stats()` with selected-window aggregates, UTC patterns, Last.fm detail and an optional exact-day query.
  - Add `enrich_from_raw()` for bounded, fill-only historical metadata repair.
  - Read play aggregates only from `listening_events`; preserve user/server scoping and current 400-row `recent` behavior.
  - Run enrichment from the existing background bootstrap after linking/backfill.
- `downtify/lastfm_history.py`
  - Expose the existing import-state read through a small public function for Stats.
- `downtify/spotify_history.py`
  - Invoke fill-only enrichment after a successful sweep when a listening store is available, so late raw payload enrichment reaches canonical rows without a restart.
- `downtify/stats.py`
  - Forward the new aggregates into `build_stats()`.
  - Fix `best_day` to use the maximum count.
  - Preserve existing `total`, `measured`, `top_tracks`, `recent`, `top_contexts` and Spotify fields.
- `downtify/collections_api.py`
  - Validate and pass `date`.
  - Keep the empty-activity response shape in sync.

### Frontend

- `frontend/src/model/stats.js`
  - Send the selected date.
  - Add background day loading, separate day error state and a request sequence guard.
- `frontend/src/views/StatsView.vue`
  - Add Listening profile, UTC patterns and Last.fm detail.
  - Relabel the measured card.
  - Use `playback.day.plays` for a selected day and show exact/truncated counts plus retry.
- `frontend/src/components/library/ActivityHeatmap.vue`
  - Date-keyed hover state, gap-safe delegated handlers, localized tooltip, 2D roving focus, stable selected outline and coarse-pointer targets.
- `frontend/src/lib/heatmap.js`
  - Add a small pure key-resolution helper for the 2D grid.
- Eight locale files
  - Add profile, UTC pattern, Last.fm, coverage, play-count, keyboard-hint and day-state strings; keep key parity.

### Documentation

- `docs/features/stats.md`
  - Explain measured vs track time, stored/imported coverage, source split, unique counts, UTC patterns, Last.fm detail, enrichment and corrected heatmap/day behavior.
  - Change the stale “trend line” wording to the block chart actually rendered.
- `docs/api-reference.md`
  - Document `date` and all additive fields.

## Testing and acceptance

Test-first, with separate commits:

1. **Backend contract**
   - Period totals/source split use canonical rows and respect 7/30/90 UTC windows.
   - Multi-source observations count once.
   - Unique counts exclude empty names.
   - Track-time sum and duration coverage are correct; measured seconds stay unchanged.
   - Hour/weekday buckets use UTC and sum to the period total.
   - Last.fm loved/MBID counts use distinct linked canonical events; malformed raw JSON does not break Stats.
   - Import state and imported count are read without provider calls.
   - Exact-day query is scoped, capped and reports the true total; invalid dates return 400.
   - Busiest day is an older maximum, not the newest active day.
   - Empty-activity fallback has the new keys.
2. **Historical enrichment**
   - Blank albums/context are filled from linked raw rows.
   - Non-empty Downtify values are preserved.
   - Source, identity, timestamp and canonical count do not change.
   - A second run makes no further changes.
   - Spotify late raw-context enrichment reaches the canonical row through the sweep path.
3. **Heatmap behavior**
   - Gap crossing preserves hover; refreshed data updates the hovered date.
   - Exactly one tab stop; key resolver covers ±1, ±7, Home/End and activation.
   - Selected and focus rings do not disappear on hover.
   - Tooltip text is localized and has tooltip semantics.
   - Client-mode SFC compilation stays valid.
4. **Stats UI/model**
   - Date is sent; background day loads do not toggle whole-page loading.
   - Stale responses are ignored.
   - Selected-day list uses server day plays, including a day older than the 400-row recent page.
   - New panels render zero/empty states and all eight locales build.
5. **Regression gates**
   - Narrow pytest and Vitest suites go RED before implementation and GREEN after.
   - Full pytest, Vitest, Ruff, frontend build and docs build.
   - Independent review before merge/deploy.
   - Live health and browser checks at desktop/mobile widths, keyboard-only navigation and reduced motion.

## Non-goals

- True Spotify/Last.fm listening seconds, completion or skip rates.
- Current Last.fm loved-track list or new provider calls.
- Local-time pattern claims without a stored user timezone.
- New audio providers, database migrations, public sharing, OIDC or upstream merges.
- Changing existing API field meanings or the v4 visual identity.

## Risks and mitigations

- **Duration misread as listening time:** separate labels, coverage counts and docs; measured card remains Downtify-only.
- **Partial provider history:** use “stored/imported” wording; no lifetime-total claims.
- **Album undercount:** label “known albums” and document remaining provider metadata gaps.
- **UTC/local mismatch:** label patterns UTC and preserve explicit UTC date formatting.
- **Loved flag mistaken for current state:** label it “loved at import”.
- **Background fetch races/focus loss:** request sequence guard, separate loading/error state and no page-level skeleton for day changes.
- **Enrichment overwrites better data:** fill-only updates, precedence tests and idempotence check.
- **Response growth:** only the selected day is fetched, capped at 400 plays with an exact total.

## Approval and next step

The user selected deep analytics and explicitly authorized automatic approval and implementation. The next artifact is the test-first implementation plan; production code follows that plan in separate commits with independent review and verified deploy.
