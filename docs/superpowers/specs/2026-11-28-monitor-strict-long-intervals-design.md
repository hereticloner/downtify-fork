# Monitor: strict day-or-longer intervals

- **Date:** 2026-11-28
- **Status:** Implemented
- **Scope:** `downtify/monitor.py`, monitor quiet-pass tests and current playlist-monitor docs

## Intent

Make the Monitor's visible interval truthful for daily and longer playlists. The user expects “Every day” to mean every day; currently three quiet passes silently change the effective interval to seven days while the UI still shows the configured daily value.

## Decision

Keep quiet-pass relaxation only for intervals shorter than one day. Daily, weekly, two-week and monthly playlist watches always use their configured interval, even after many quiet passes.

## Goals

- `effective_interval_minutes(1440, quiet_passes)` remains `1440` for any quiet count.
- The same strict behavior applies to every interval `>= 1440`.
- Sub-day intervals (15 minutes through 12 hours) keep the existing 3-quiet-pass / 7× relaxation.
- Existing overdue daily watches become due on the next monitor sweep without a database migration.
- Docs describe the split accurately.

## Non-goals

- Do not remove quiet-pass tracking or sub-day relaxation.
- Do not change artist-watch behavior, manual checks, sync-time anchoring or API response shapes.
- Do not add a new setting or per-playlist toggle.

## Alternatives

1. **Strict day-or-longer intervals (chosen).** Smallest change that matches the user's expectation while preserving the existing optimization for frequently checked playlists.
2. **Disable relaxation for every interval.** Simpler rule but increases API/traffic for unchanged hourly and six-hour watches.
3. **Keep relaxation and show the effective interval in the UI.** Preserves current behavior but still violates the user's expectation that daily means daily.

## Acceptance

- Tests prove daily/weekly/monthly intervals never relax and sub-day intervals still relax at the threshold.
- A regression test proves a daily watch last checked more than 24 hours ago is due even with `quiet_passes >= 3`.
- Current docs no longer claim a daily watch becomes weekly.
- Existing monitor/API/frontend tests and builds pass; no schema/API/dependency change.
