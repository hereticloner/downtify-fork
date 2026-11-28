# Stats: Last.fm + Downtify source model and fresh recent plays

- **Date:** 2026-11-27
- **Status:** Implemented
- **Scope:** Canonical listening source precedence/reconciliation, Stats aggregate and detail queries, history refresh startup, StatsView source presentation, tests and current docs

## Intent

Make Stats a Last.fm-led personal history with Downtify local plays, remove Spotify-only plays from what Stats counts, and restore a truthful current “Son çalınanlar” list.

The user chose this after measuring that Spotify and Last.fm are already merged, but source badges and unmatched provider metadata make them look separate. Last.fm is the preferred historical source; Spotify Connect and Spotify Sync remain separate features.

## Goals

- Stats counts only canonical plays observed by Downtify or Last.fm.
- On a merged play, Downtify wins when present; otherwise Last.fm supplies the Stats source, timestamp and track metadata.
- Spotify-only canonical rows remain stored but do not affect Stats totals, recent plays, top lists, periods, day detail or pattern detail.
- Recent plays catch up to provider data on startup and continue refreshing; failures are visible in logs rather than silently looking like stale success.
- Stats source UI shows only Downtify and Last.fm.

## Non-goals

- Do not delete raw Spotify rows, Spotify-only canonical rows or legacy top-level `spotify` API fields.
- Do not disable Spotify Connect, Spotify Sync or Spotify raw-history collection.
- Do not add providers, dependencies, public sharing, OIDC or upstream merges.
- Do not change Technical Gazette styling, compact typography, covers, eight locales or reduced-motion behavior.
- Do not broaden fuzzy title matching. Spotify-only duplicates disappear because Spotify is excluded, not because uncertain matches are forced together.

## Constraints

- `listening_events.id`, `identity_key` and all `listening_event_sources` links stay stable.
- Raw Spotify and Last.fm observations stay untouched and backed up.
- `by_source` keeps the existing `spotify` key at zero for API compatibility.
- Known listening seconds/completions/skips still come only from Downtify position reports.
- Last.fm remains the historical source; Downtify remains authoritative for an actual local player event.

## Approaches considered

1. **Last.fm + Downtify Stats projection (chosen).** Change canonical precedence to Downtify → Last.fm → Spotify, idempotently reconcile existing Last.fm-linked rows, and filter every Stats read to Downtify/Last.fm winners. Spotify raw data and non-Stats features remain intact. Smallest model that matches the user's choice without deleting history.
2. **Last.fm-first union with Spotify fallback.** Keep Spotify-only plays and prefer Last.fm on overlap. More coverage, but contradicts the selected source model and still needs uncertain duplicate handling.
3. **UI-only Spotify filter.** Hide Spotify labels/rows without changing totals or canonical precedence. Rejected: totals would still include Spotify and merged Last.fm plays could disappear because Spotify currently wins.

## Design

### Canonical source rules

- `_SOURCE_PRIORITY` becomes `downtify: 0`, `lastfm: 1`, `spotify: 2`.
- New Last.fm observations promote a merged Spotify winner; new Spotify observations cannot replace Last.fm.
- Add an idempotent reconciliation pass for existing events that have a Last.fm source link and no Downtify link:
  - set canonical `source='lastfm'`, `source_key`, `played_at`, `title`, `artist` and `album` from the linked Last.fm raw row;
  - clear Spotify-derived `duration_ms`, `context` and `context_type`, so Stats does not attribute Spotify duration/context to Last.fm;
  - preserve `id`, `identity_key`, `match_key`, source links and raw rows.
- Events with a Downtify link keep Downtify metadata. Spotify-only events are not reconciled or deleted.

### Stats reads

- `ListeningStore.stats()`, `day_plays()` and `pattern_detail()` include only canonical winners with `source IN ('downtify', 'lastfm')`.
- This applies to totals, profile range, unique counts, top tracks/artists/albums, recent rows, source counts, weeks, selected periods, known-time coverage, day detail and pattern detail.
- `profile.by_source`, `period.by_source` and detail `by_source` retain `spotify: 0`.
- Legacy top-level `spotify.recent` / `spotify.play_count` remain outside the Stats profile for compatibility; StatsView does not render them.

### Freshness

- Add a bounded immediate provider catch-up during application startup, before the server reports startup complete:
  - one Last.fm newest-page pass (`max_pages=1`);
  - one Spotify recently-played page;
  - reuse existing `run_once` functions and existing settings/switches;
  - run concurrently with isolated error summaries and never expose credentials.
- Keep the existing periodic loops. Log saved plays and fetch/connection errors at INFO; keep empty successful sweeps quiet so a stalled refresh is diagnosable without noisy logs.
- Startup catch-up is bounded by existing provider timeouts; failed providers do not block health/startup.
- Persist any renewed Spotify tokens through the existing settings writer. Deployment verification must confirm `/data/settings.json` is writable by the container user; the current host copy is root-owned and produces permission warnings.

### UI

- Stats source rows and recent badges contain only Downtify and Last.fm.
- Source bar styling keeps Downtify as the solid ink row and Last.fm as the quiet row.
- Existing `stats.sourceSpotify` translations remain for compatibility but are not rendered by StatsView.
- Update the Spotify “Import listening history” hint in all eight locales: Spotify history is stored separately and is not a Stats source; the existing reconnect/scope warning remains.

## Acceptance

- Regression tests prove Spotify-only plays are excluded from Stats while Last.fm-linked merged plays and Downtify+Spotify local plays remain.
- Reconciliation tests prove Last.fm metadata/time wins without retaining Spotify duration/context or changing identities/links.
- Day and pattern detail tests match the main Stats totals and never return Spotify winners.
- Startup catch-up tests prove both provider `run_once` paths are invoked once and provider failure does not fail startup.
- Frontend tests prove only two source rows/labels render and legacy Spotify translation keys remain intact.
- Live check after deploy: newest local play matches the provider's newest play within one refresh interval; “Son çalınanlar” has no Spotify badge; Stats totals exclude the measured Spotify-only set.
- Full backend/frontend/docs tests, Ruff and builds pass. No schema, dependency or raw-data deletion diff.

## Risks

- About 692 currently stored Spotify-only canonical plays will leave Stats aggregates; the user accepted this trade-off.
- Existing merged rows will show Last.fm timestamps/metadata after reconciliation, so some displayed times may shift by minutes.
- Last.fm misses will no longer be filled by Spotify in Stats; only Downtify can cover those plays.
