# Stats Context Names + Interactive Listening Patterns

- **Date:** 2026-11-26
- **Status:** Approved — implementation authorized
- **Branch:** `feat/personal-server-program`
- **Base:** `826a964`

## Intent

Make Stats feel inspectable rather than ornamental. The user should see human-readable Spotify context names instead of raw URIs, and should be able to hover, focus and click the UTC Listening Patterns bars to inspect the plays behind an hour or weekday.

## Why now

The deep Stats wave shipped correct aggregates but left two UI gaps:

- Spotify Recently Played context objects contain `type` and `uri`, not `name`. Downtify stores the URI and the current UI renders it verbatim in **Most played from** and context badges.
- Listening Patterns currently renders 24 hour bars and seven weekday bars as a static `role="img"`; there is no selection or bucket-level detail.

A deterministic synthetic repro confirms the raw URI reaches `top_contexts[0].context` unchanged. Official Spotify docs confirm the context object has no display name.

## Goals

- Replace raw Spotify context URIs in every Stats context surface with a resolved name when available, otherwise a localized type label such as “Spotify playlist”.
- Resolve playlist, artist and album names through the existing Spotify OAuth connection in the background.
- Keep Stats reads fast and available when Spotify is offline, rate-limited, unauthenticated or refuses a private resource.
- Make hour/weekday bars real buttons with hover/focus feedback, one tab stop per chart, keyboard movement and a selected state.
- On selection, show exact period-scoped bucket detail: total, canonical source split, top tracks, top artists and recent plays.
- Preserve v4 identity, eight locales, reduced-motion behavior, API compatibility and port `8000`.

## Non-goals

- Re-fetching or rewriting canonical play history.
- New audio providers, OIDC, PostgreSQL, public sharing or upstream merges.
- Resolving arbitrary non-Spotify URIs.
- Showing a provider's complete lifetime stats.
- Blocking the Stats page on a live Spotify call.
- Adding a new dependency.

## Anti-goals

- No raw `spotify:*` URI as the primary visible label.
- No invented name when resolution fails.
- No client-side filtering of the 400-row recent sample presented as exact bucket detail.
- No bar/detail mismatch caused by different UTC predicates.
- No stale background response overwriting a newer selection.
- No scope creep into a general Spotify browser.

## Constraints

- Canonical play counts come only from `listening_events`; raw provider rows remain provenance.
- Selected-window and bucket semantics are UTC: today plus the preceding `days - 1` days.
- `days` remains `7`, `30` or `90`.
- Existing fields keep their meaning; new response fields are additive.
- Spotify calls use the existing mirror OAuth tokens and token-persistence path.
- The context cache lives in `downtify_activity.db` and is included in backups.
- Live name resolution is best-effort: deleted, private or inaccessible resources keep the type fallback until a later successful refresh.

## Approaches considered

### A — UI-only quick pass

Turn bars into buttons, show count/share tooltips, and filter the existing 400 recent plays client-side. Format Spotify URIs into type labels.

- **Pros:** smallest change, no backend work.
- **Cons:** bucket detail is only a recent sample; no exact source split or top tracks/artists; easy to misrepresent.
- **Decision:** rejected because the user asked for detailed inspection.

### B — Exact bucket detail, local labels only

Add an additive bucket query and rich detail panel. Context labels use URI type fallback plus any existing local playlist cache entry.

- **Pros:** truthful detail, no provider calls.
- **Cons:** artist/album names and uncached playlist names remain generic.
- **Decision:** not chosen; the user explicitly selected live Spotify names.

### C — Exact bucket detail + live Spotify name resolution (chosen)

Implement B and add a persistent, background Spotify context-name cache resolved through the existing OAuth connection.

- **Pros:** truthful drilldown and real names where Spotify permits access; Stats remains resilient.
- **Cons:** one new cache table, a background resolver, rate-limit/error handling and backup coverage.
- **Decision:** chosen by the user.

## Current data flow

1. `spotify_history.parse_plays()` stores `item.context` as raw JSON.
2. `spotify_history.link_pending()` copies `context.uri` into canonical `context` and `context.type` into `context_type`.
3. `ListeningStore.stats()` groups canonical `context` values into `top_contexts`.
4. `StatsView.vue` renders `row.context` directly in **Most played from** and context badges.
5. Patterns expose only aggregate arrays; no bucket-detail endpoint exists.

Downtify-origin contexts remain human-readable queue titles. Last.fm has no context. The raw-label problem is Spotify-specific.

## User experience

### Context labels

- Every Stats context surface uses one formatter:
  1. cached resolved name, when present;
  2. localized `Spotify playlist`, `Spotify artist` or `Spotify album`, parsed from the URI;
  3. the original Downtify queue title for non-Spotify contexts.
- The raw URI is retained in the API for compatibility and diagnostics, but is not the primary visible text.
- Names appear after a background resolver pass. Until then the type fallback is immediately useful.
- A failed resolution never removes the play or breaks Stats.

### Interactive Patterns

- Each chart is a real button group with one tab stop.
- Hover or focus shows a tooltip with the localized bucket label, exact count and share of the selected period.
- Arrow Left/Right moves one bucket; Home/End jumps to the edges; Enter/Space selects.
- The selected bar keeps an accent outline on hover and focus.
- Fine pointers keep compact bars; coarse pointers get at least 24px targets and horizontal scrolling where needed.
- Tooltip motion is disabled under `prefers-reduced-motion`.

### Bucket detail panel

Selecting an hour or weekday opens a panel below the charts with:

- clear title, for example `Hour 14:00–14:59 UTC` or `Sunday UTC`;
- exact canonical play total;
- Downtify / Spotify / Last.fm split;
- top five tracks and top five artists;
- up to 50 newest plays, with provider and formatted context badges;
- a truncation note when more plays exist;
- skeleton while loading, inline retry on failure and an explicit empty state.

A **Clear** button removes the selection. Selecting a heatmap day clears the pattern selection; selecting a pattern clears the heatmap day. This keeps one drilldown scope unambiguous. Period changes keep the selection and reload its detail.

## Backend contract

### Exact bucket query

Add:

```python
ListeningStore.pattern_detail(
    user_id: int,
    days: int,
    kind: str,          # "hour" | "weekday"
    bucket: int,        # hour 0..23 | weekday 0..6
    *,
    top_limit: int = 5,
    recent_limit: int = 50,
) -> dict[str, Any]
```

Return:

```json
{
  "kind": "hour",
  "bucket": 14,
  "total": 40,
  "by_source": { "downtify": 2, "spotify": 35, "lastfm": 3 },
  "top_tracks": [{ "summary": "Artist - Title", "count": 8 }],
  "top_artists": [{ "artist": "Artist", "count": 12 }],
  "recent": [
    {
      "at": "2026-11-25T14:15:00+00:00",
      "date": "2026-11-25",
      "summary": "Artist - Title",
      "context": "spotify:playlist:...",
      "context_type": "playlist",
      "source": "spotify"
    }
  ],
  "truncated": true
}
```

The query must reuse the exact selected-window predicate and the same `strftime('%H', played_at)` or `strftime('%w', played_at)` expression as `patterns`. Counts remain canonical and user/server scoped. Empty names are excluded from top artists. Recent rows are newest first.

### Stats endpoint

Add optional query parameters:

- `pattern=hour|weekday`
- `bucket=0..23|0..6`

Both must be supplied together; invalid or out-of-range values return `400`. Add `playback.pattern_detail` with an empty default when omitted. `date=` semantics do not change.

Add `playback.context_labels`, an object mapping canonical Spotify context URI to cached display name. Only names relevant to the current response are returned. Missing cache/table means `{}`.

The `activity is None` fallback receives both additive keys.

### Context-name cache

Add `spotify_context_cache` to `downtify_activity.db`:

```text
context_key   TEXT PRIMARY KEY   -- normalized spotify:<kind>:<id>
kind          TEXT NOT NULL      -- playlist | artist | album
name          TEXT NOT NULL DEFAULT ''
fetched_at    TEXT NOT NULL DEFAULT ''
last_error    TEXT NOT NULL DEFAULT ''
retry_at      TEXT NOT NULL DEFAULT ''
```

Add a focused `downtify/spotify_context.py` module responsible for:

- schema creation;
- URI/URL parsing and normalization for playlist, artist and album;
- cache reads for Stats;
- bounded background resolution;
- token refresh/persistence through the existing mirror helpers;
- backup-compatible table metadata.

Resolution endpoints:

- `GET /v1/playlists/{id}`
- `GET /v1/artists/{id}`
- `GET /v1/albums/{id}`

Behavior:

- Stats GET reads cache only and never calls Spotify.
- A background loop runs every 15 minutes when the Spotify mirror is enabled and usable.
- Each pass resolves at most 25 distinct unresolved/stale contexts, oldest first, with at least one second between calls.
- Successful names refresh after 30 days.
- Errors retry after six hours; `404` after 24 hours.
- `429` honors `Retry-After` and stops the pass.
- `401/403` stops the pass; private/inaccessible resources keep the type fallback and remain retryable.
- Renewed tokens use the existing persistence callback.
- No secrets or full provider error bodies are logged.

Add the table to `downtify/backup.py` table and primary-key lists so metadata backups preserve it.

## Frontend structure

### New focused files

- `frontend/src/components/library/ListeningPatterns.vue`
  - hour/weekday button charts, roving focus, tooltip, selection and coarse-pointer targets;
  - emits `select({kind, bucket})` and `clear`.
- `frontend/src/lib/pattern.js`
  - pure key resolver and count/share helpers.
- `frontend/src/lib/context.js`
  - pure Spotify URI parser and display-label fallback helper.

### Modified files

- `frontend/src/model/stats.js`
  - add `patternLoading`, `patternError`, selected-pattern state and `loadPattern()`;
  - retain stale-response protection;
  - background day/pattern loads merge only their detail field instead of replacing the whole Stats object;
  - a newer base-period request invalidates older detail requests.
- `frontend/src/views/StatsView.vue`
  - render `ListeningPatterns` and the detail panel;
  - enforce day/pattern mutual exclusion;
  - use the shared context formatter in top contexts, recent/day plays and pattern detail;
  - keep existing profile and heatmap behavior.
- Eight locale files
  - add context type labels, pattern tooltip/detail/loading/error/truncation strings.

No new charting or UI dependency is added.

## Accessibility and responsive behavior

- Counts are available as text and accessible names; color is not the only channel.
- Tooltips use `role="tooltip"` and `aria-describedby`.
- Selected bars use `aria-pressed`.
- Detail loading uses `aria-busy`; errors have an inline retry button.
- Long names wrap instead of truncating critical detail; compact badges may truncate with a tooltip.
- Reduced motion removes tooltip transitions.
- Mobile charts scroll horizontally when required; the detail panel is full width.

## Testing and acceptance

Test-first, separate commits:

1. **Context formatter/cache**
   - URI and Spotify URL parsing for playlist/artist/album.
   - Resolved name wins; missing name falls back to localized type; Downtify titles pass through.
   - Cache schema, normalization, TTL/retry and backup table coverage.
   - Fake-provider resolver tests for success, 401/403, 404, 429 `Retry-After`, malformed body and token renewal.
   - Stats remains cache-only on the request path.
2. **Pattern detail API**
   - Exact total equals the corresponding bar count.
   - Source split uses canonical winners and multi-source observations count once.
   - Top tracks/artists and recent caps are correct.
   - UTC boundary, user/server scope and invalid parameter tests.
   - Empty-activity response parity.
3. **Patterns interaction**
   - One tab stop per chart; Left/Right/Home/End/Enter/Space behavior.
   - Hover/follow-refresh tooltip, selection outline and reduced-motion rules.
   - Day/pattern mutual exclusion.
4. **Stats model/UI**
   - Pattern request parameters, background loading, stale-response guard and inline error state.
   - Detail uses server rows, not filtered recent sample.
   - All context surfaces use resolved/fallback labels.
   - Client-mode SFC compilation and eight-locale parity.
5. **Regression gates**
   - Narrow RED→GREEN tests per task.
   - Full pytest, Vitest, Ruff, frontend/docs builds.
   - Independent whole-branch review.
   - Verified deploy and live cache-only Stats response.

## Rollout

1. Merge approved commits into `feat/collections` by fast-forward.
2. Deploy with the existing deploy script.
3. Verify health, additive API fields and the new backup table.
4. Let the background resolver fill names; confirm fallback labels immediately and resolved names after a pass.
5. Browser-check desktop/mobile, keyboard-only navigation and reduced motion.

## Risks and mitigations

- **Spotify scope/permission limits:** fallback label remains useful; no forced reconnect or blocked Stats.
- **Rate limiting:** bounded batch, spacing, `Retry-After`, persistent retry time and no request-path calls.
- **Stale names:** 30-day refresh; canonical URI remains the identity.
- **Cache growth:** one row per distinct normalized context, not per play.
- **Bar/detail drift:** shared UTC window and bucket expressions, with a test asserting equal totals.
- **Response races:** separate detail state with a global request sequence and field-level merge.
- **Backup omission:** explicit table/key registration and restore test.
- **UI regressions:** focused component, client-compile test, locale parity and independent review.

## Builder-check resolutions

- **Queue source and order:** scan distinct canonical `listening_events.context` values that have a `spotify` row in `listening_event_sources`, normalized to `spotify:<kind>:<id>`. Order unresolved/stale keys by `MIN(played_at)` so the oldest displayed histories resolve first. Raw-only contexts are not queued because they are not visible in Stats until linked.
- **Enable condition:** the resolver runs when the `spotify_mirror` block is enabled and has a client id plus an access or refresh token. It does **not** require `import_recent` or a playback device id; name resolution is metadata work, not listening import or playback.
- **Account/token scope:** mirror settings and OAuth are server-global. Resolve all canonical contexts with Spotify provenance using that one configured account. Current Spotify import assigns those plays to the first admin; no user identity or listening history is sent to Spotify, only public resource IDs.
- **Detail-only labels:** every Stats response gathers cached labels for all context URIs present in that response, including selected-day and pattern-detail rows. Background pattern loads merge both `pattern_detail` and `context_labels`; day loads merge both `day` and `context_labels`. The raw URI never becomes the fallback label for a recognized Spotify context.
- **Accepted URI forms:** normalize `spotify:<kind>:<id>`, `spotify:user:<user>:playlist:<id>`, `https://open.spotify.com/<kind>/<id>` with query/localized prefixes, and legacy API hrefs such as `https://api.spotify.com/v1/playlists/<id>`. Unknown or unsupported forms retain the original non-Spotify text or a generic Spotify label when the type is known.

## Approval requested

Approve this design to produce the test-first implementation plan. No production code for this new wave will change before approval.
