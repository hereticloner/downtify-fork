# Monitor Strict Long Intervals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make daily and longer Monitor intervals exact while retaining quiet-pass relaxation for sub-day playlist watches.

**Architecture:** Add one boundary in `effective_interval_minutes()`: intervals at or above `MINUTES_PER_DAY` return unchanged; shorter intervals keep the existing threshold/multiplier. Update behavior tests and current docs; no schema/API/UI change is needed because the displayed configured interval becomes truthful.

**Tech Stack:** Python, pytest, existing FastAPI monitor list route, Markdown/VitePress docs

**Spec:** `docs/superpowers/specs/2026-11-28-monitor-strict-long-intervals-design.md`

## Global Constraints

- Intervals `>= 1440` minutes always use the configured interval.
- Sub-day intervals keep the existing 3-quiet-pass / 7× relaxation.
- Do not change artist-watch behavior, manual checks, sync-time anchoring or API response shapes.
- Do not add a setting, per-playlist toggle, dependency or database migration.
- Preserve existing monitor/API/frontend behavior outside the interval calculation.

## Review Focus

- A daily watch with many quiet passes is due after 24 hours — Task 1 route-level regression.
- Weekly, two-week and monthly intervals never relax — Task 1 parameterized boundary assertions.
- Sub-day intervals still relax only at the threshold — Task 1 existing threshold tests.
- A new track still resets quiet passes — Task 1 existing reset test.
- Artist watches and manual checks remain untouched — Task 1 focused monitor suites and diff scope.

---

### Task 1: Strict day-or-longer Monitor intervals

**Files:**
- Modify: `downtify/monitor.py`
- Test: `tests/test_monitor_quiet.py`
- Modify: `docs/features/playlist-monitor.md`
- Modify: `docs/superpowers/specs/2026-11-28-monitor-strict-long-intervals-design.md`

**Interfaces:**
- Consumes: `effective_interval_minutes(interval_minutes: int, quiet_passes: int) -> int`, `MINUTES_PER_DAY`, existing monitor list route.
- Produces: unchanged function signature; day-or-longer values are never multiplied.

- [ ] **Step 1: Update and add failing behavior tests**

In `test_effective_interval_relaxes_at_the_threshold`, keep the sub-day assertions and replace the daily relaxation expectation with strict values for `1440`, `10080`, `20160` and `43200` minutes at quiet counts `3` and `9`.

Add `test_next_due_minutes_daily_stays_strict_after_many_quiet_passes`: create a daily watch, set `last_checked` to 25 hours ago and `quiet_passes=5`, call `api.list_monitor_playlists()`, and assert `next_due_minutes == 0`.

- [ ] **Step 2: Run the tests and verify RED**

Run: `.venv/bin/pytest -q tests/test_monitor_quiet.py -k 'effective_interval_relaxes_at_the_threshold or daily_stays_strict'`
Expected: FAIL because daily currently becomes 10080 minutes.

- [ ] **Step 3: Implement the boundary**

At the start of `effective_interval_minutes()`, return the configured value when `interval_minutes >= MINUTES_PER_DAY`; leave the existing quiet-pass branch unchanged for shorter intervals.

- [ ] **Step 4: Run the tests and verify GREEN**

Run: `.venv/bin/pytest -q tests/test_monitor_quiet.py -k 'effective_interval_relaxes_at_the_threshold or daily_stays_strict'`
Expected: PASS.

- [ ] **Step 5: Update current docs and spec status**

Rewrite the quiet-pass section to say only sub-day watches relax; daily and longer watches keep their configured interval. Update the daily-sync note that currently says empty playlists are checked less often. Mark the spec Implemented.

- [ ] **Step 6: Run affected suites and static checks**

Run: `.venv/bin/pytest -q tests/test_monitor*.py`
Expected: PASS.

Run: `.venv/bin/ruff check downtify/monitor.py tests/test_monitor_quiet.py`
Expected: PASS.

Run: `npm test && npm run build` in `docs/`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add downtify/monitor.py tests/test_monitor_quiet.py docs/features/playlist-monitor.md docs/superpowers/specs/2026-11-28-monitor-strict-long-intervals-design.md
git commit -m "fix(monitor): keep daily and longer intervals strict"
```
