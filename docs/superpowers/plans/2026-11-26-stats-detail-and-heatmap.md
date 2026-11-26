# Stats Detail and Heatmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add truthful deep listening analytics to Downtify Stats and repair the GitHub-style heatmap's data, keyboard, pointer and selected-day behavior.

**Architecture:** Compute additive selected-window aggregates from the canonical `listening_events` table; repair missing canonical metadata from already-linked raw provider rows with a fill-only background pass; keep all existing Stats fields stable. The frontend adds profile/pattern/Last.fm panels and fetches exact-day plays in the background while the heatmap becomes a localized, one-tab-stop 2D control.

**Tech Stack:** Python/FastAPI/SQLite, Vue 3/Vite/Vitest, existing i18n and Tailwind design tokens; no new dependencies.

**Spec:** `docs/superpowers/specs/2026-11-26-stats-detail-and-heatmap-design.md`

## Global Constraints

- Private, self-hosted Downtify only; no per-user libraries, public sharing, OIDC, new audio providers, PostgreSQL or full upstream merges.
- Preserve v4 identity, reduced-motion behavior, existing API semantics, all eight locales and port `8000`.
- Canonical play counts come only from `listening_events`; raw Spotify/Last.fm rows are provenance, never extra plays.
- Never fabricate measured seconds, completions or skips for Spotify/Last.fm.
- Selected-window metrics use UTC calendar days: today plus the preceding `days - 1` days; `days` is `7`, `30` or `90`.
- No new provider calls, tables or dependencies. Historical enrichment runs in the background, never in a Stats GET.
- Test-first, separate commits, independent review, fast-forward integration into `feat/collections`, verified deploy.
- Work in `/home/yeet/downtify/.worktrees/personal-server-program` on `feat/personal-server-program`.

## Review Focus

- **Multi-source observations:** one real play linked to Downtify, Spotify and Last.fm must remain one canonical play in every aggregate.
- **Partial/malformed provider data:** missing durations, empty album names, malformed Last.fm JSON and incomplete backfill must produce honest zero/coverage states, never a 500 or fabricated value.
- **UTC boundaries:** events at the first/last instant of the window and on a selected day must land in exactly the intended UTC bucket.
- **Fill-only enrichment:** richer Downtify context/album and canonical identity/count must never be overwritten by raw provider metadata.
- **Background day loading:** rapid day/period changes must not apply stale responses, blank the page or steal heatmap focus.

## File Structure

- `downtify/listening_history.py` — canonical selected-window aggregates, exact-day plays, Last.fm detail and fill-only raw metadata enrichment.
- `downtify/lastfm_history.py` — public read-only import-state accessor.
- `downtify/spotify_history.py` — run enrichment after a successful sweep.
- `downtify/stats.py` — additive response shaping and correct busiest-day selection.
- `downtify/collections_api.py` — `date` validation, scoped data plumbing and empty-response parity.
- `frontend/src/lib/heatmap.js` — pure 2D key resolver.
- `frontend/src/components/library/ActivityHeatmap.vue` — accessible, localized, gap-safe heatmap interaction.
- `frontend/src/model/stats.js` — request sequencing, background day state and selected-day row helper.
- `frontend/src/views/StatsView.vue` — profile, UTC patterns, Last.fm detail and exact-day panel.
- `frontend/src/i18n/locales/*.js` — eight localized Stats surfaces.
- `tests/test_api_stats.py`, `tests/test_listening_history.py`, `tests/test_lastfm_history.py`, `tests/test_spotify_history.py` — backend contracts.
- `frontend/src/__tests__/heatmap.test.js`, `heatmapInteraction.test.js`, `statsPeriod.test.js`, `statsViewClientRender.test.js`, `statsLocale.test.js` — frontend contracts.
- `docs/features/stats.md`, `docs/api-reference.md` — user/API truth.

---

### Task 0: Commit the approved design and plan

**Files:**
- Modify: `docs/superpowers/specs/2026-11-26-stats-detail-and-heatmap-design.md`
- Create: `docs/superpowers/plans/2026-11-26-stats-detail-and-heatmap.md`

- [ ] Confirm the design status is `Approved — deep analytics scope; implementation authorized`.
- [ ] Confirm the worktree contains only the two intended documentation files.
- [ ] Commit both files as `docs(stats): approve deep analytics and heatmap design`.

### Task 1: Canonical period aggregates and correct busiest day

**Files:**
- Modify: `downtify/listening_history.py:288-363`
- Modify: `downtify/stats.py:228-358`
- Modify: `downtify/collections_api.py:339-421`
- Test: `tests/test_listening_history.py`
- Test: `tests/test_api_stats.py`

**Interfaces:**
- Consumes: existing `ListeningStore.link_or_create()` and canonical schema.
- Produces: `ListeningStore.stats(user_id=0, recent_limit=400, *, days=30) -> dict` with additional `period`, `unique`, `track_time` and `patterns` keys; existing keys unchanged.

- [ ] **Step 1: Write failing canonical aggregate tests**

```python
def test_period_aggregates_count_canonical_events_once():
    # Same artist/title within the match window from Spotify + Last.fm.
    data = store.stats(days=7)
    assert data['period'] == {
        'days': 7,
        'total': 1,
        'by_source': {'downtify': 0, 'spotify': 1, 'lastfm': 0},
    }


def test_period_aggregates_report_unique_duration_and_utc_patterns():
    # Two in-window events, one outside; known durations 5000ms and 0.
    assert data['unique'] == {'tracks': 2, 'artists': 1, 'albums': 1}
    assert data['track_time'] == {
        'seconds': 5,
        'plays_with_duration': 1,
        'plays_without_duration': 1,
    }
    assert sum(data['patterns']['by_hour']) == 2
    assert sum(data['patterns']['by_weekday']) == 2
```

Add endpoint assertions that `days=7|30|90` changes only selected-window aggregates and that `playback.total` remains all stored canonical plays.

- [ ] **Step 2: Run the narrow tests and verify RED**

Run: `ssh home 'docker exec downtify-feature-py sh -lc "cd /work && uv run pytest tests/test_listening_history.py tests/test_api_stats.py -q"'`

Expected: FAIL because the new keys do not exist.

- [ ] **Step 3: Implement the aggregate contract**

Add a UTC `window_start`/`window_end` predicate shared by all selected-window queries. `period.by_source` always has Downtify/Spotify/Last.fm keys. Count unique non-empty track keys/names, positive durations and UTC `%H`/`%w` buckets. Exclude future timestamps. Keep raw tables out of play totals.

- [ ] **Step 4: Write the busiest-day regression test**

```python
def test_best_day_is_the_older_maximum_not_the_newest_active_day(client):
    # Older day has 40 plays; newest active day has 1.
    assert client.get('/api/stats').json()['playback']['best_day'] == {
        'date': older.isoformat(),
        'count': 40,
    }
```

- [ ] **Step 5: Run the regression test and verify RED**

Run: `ssh home 'docker exec downtify-feature-py sh -lc "cd /work && uv run pytest tests/test_api_stats.py::test_best_day_is_the_older_maximum_not_the_newest_active_day -q"'`

Expected: FAIL with the newest day's date/count.

- [ ] **Step 6: Implement response shaping and busiest-day fix**

Copy the additive keys from `listening_stats` into `playback` with zero defaults. Replace the reversed-first-active selection with `max(heatmap, key=lambda day: day['count'])`, preserving earliest ties and the empty result. Update the empty-activity branch with identical zero shapes. Pass `days=window` into `ListeningStore.stats()`.

- [ ] **Step 7: Run the narrow suite and verify GREEN**

Run: `ssh home 'docker exec downtify-feature-py sh -lc "cd /work && uv run pytest tests/test_listening_history.py tests/test_api_stats.py -q"'`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add downtify/listening_history.py downtify/stats.py downtify/collections_api.py tests/test_listening_history.py tests/test_api_stats.py
git commit -m "feat(stats): add canonical period listening aggregates"
```

### Task 2: Last.fm loved, MBID and import-state detail

**Files:**
- Modify: `downtify/lastfm_history.py:303-315`
- Modify: `downtify/listening_history.py:288-363`
- Test: `tests/test_lastfm_history.py`
- Test: `tests/test_api_stats.py`

**Interfaces:**
- Consumes: Task 1's selected-window predicate and canonical scope.
- Produces: `lastfm_history.import_state(db_path) -> dict[str, Any]`; `ListeningStore.stats()` additionally returns `lastfm`.

- [ ] **Step 1: Write failing Last.fm detail tests**

```python
def test_lastfm_detail_counts_linked_loved_and_mbid_events_once():
    assert data['lastfm']['loved_plays'] == 1
    assert data['lastfm']['mbid_plays'] == 1
    assert data['lastfm']['imported_plays'] == 2


def test_lastfm_detail_survives_malformed_raw_json():
    # One linked row has raw_json='not-json'.
    response = client.get('/api/stats')
    assert response.status_code == 200
    assert response.json()['playback']['lastfm']['loved_plays'] == 0
```

Add a user-scope test proving one account does not receive another account's loved/MBID canonical events.

- [ ] **Step 2: Run the narrow tests and verify RED**

Run: `ssh home 'docker exec downtify-feature-py sh -lc "cd /work && uv run pytest tests/test_lastfm_history.py tests/test_api_stats.py -q"'`

Expected: FAIL because `lastfm` detail is absent.

- [ ] **Step 3: Implement the public state reader and Last.fm aggregate**

Rename/wrap `_load_state` behind public `import_state()` without changing its return shape. Count distinct linked canonical events for truthy `loved` and non-empty MBID inside the selected window. Use `CASE WHEN json_valid(raw_json) THEN ... ELSE 0 END` so malformed rows are harmless. Read total imported raw rows and state without network access.

- [ ] **Step 4: Run the narrow suite and verify GREEN**

Run: `ssh home 'docker exec downtify-feature-py sh -lc "cd /work && uv run pytest tests/test_lastfm_history.py tests/test_api_stats.py -q"'`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add downtify/lastfm_history.py downtify/listening_history.py tests/test_lastfm_history.py tests/test_api_stats.py
git commit -m "feat(stats): add Last.fm detail and import coverage"
```

### Task 3: Exact selected-day plays and `date` query

**Files:**
- Modify: `downtify/listening_history.py`
- Modify: `downtify/stats.py`
- Modify: `downtify/collections_api.py:339-421`
- Test: `tests/test_listening_history.py`
- Test: `tests/test_api_stats.py`

**Interfaces:**
- Consumes: canonical event row shape from Task 1.
- Produces: `ListeningStore.day_plays(on_date: str, user_id: int = 0, limit: int = 400) -> dict[str, Any]`; `GET /api/stats?date=YYYY-MM-DD`; additive `playback.day`.

- [ ] **Step 1: Write failing exact-day tests**

```python
def test_day_plays_returns_exact_scoped_total_and_capped_rows():
    day = store.day_plays('2026-11-20', user_id=1, limit=2)
    assert day['date'] == '2026-11-20'
    assert day['total'] == 3
    assert len(day['plays']) == 2


def test_stats_date_query_rejects_invalid_dates(client):
    assert (
        client.get('/api/stats', params={'date': '2026-02-30'}).status_code
        == 400
    )
```

Add an endpoint test where the selected day predates the 400 most recent rows and still returns its play.

- [ ] **Step 2: Run the narrow tests and verify RED**

Run: `ssh home 'docker exec downtify-feature-py sh -lc "cd /work && uv run pytest tests/test_listening_history.py tests/test_api_stats.py -q"'`

Expected: FAIL because `day_plays` and `date` do not exist.

- [ ] **Step 3: Implement exact-day query and API validation**

Add `DAY_PLAYS_LIMIT = 400`. Query `COUNT(*)` and newest-first rows with `substr(played_at, 1, 10)=?`, using the same user/server scope rule as Stats. Validate the query as a real ISO calendar date and return `400` for invalid input. Pass the result into `build_stats()` and return an empty day object when omitted or activity is unavailable.

- [ ] **Step 4: Run the narrow suite and verify GREEN**

Run: `ssh home 'docker exec downtify-feature-py sh -lc "cd /work && uv run pytest tests/test_listening_history.py tests/test_api_stats.py -q"'`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add downtify/listening_history.py downtify/stats.py downtify/collections_api.py tests/test_listening_history.py tests/test_api_stats.py
git commit -m "feat(stats): add exact selected-day play queries"
```

### Task 4: Fill-only historical metadata enrichment

**Files:**
- Modify: `downtify/listening_history.py`
- Modify: `downtify/spotify_history.py:543-587`
- Test: `tests/test_listening_history.py`
- Test: `tests/test_spotify_history.py`

**Interfaces:**
- Consumes: raw Spotify/Last.fm rows already linked by `listening_event_id`.
- Produces: `ListeningStore.enrich_from_raw(batch_size: int = 500) -> int`; bootstrap and Spotify sweep call it in worker threads.

- [ ] **Step 1: Write failing enrichment tests**

```python
def test_enrichment_fills_only_blank_canonical_metadata():
    # Spotify raw row has album/context; canonical row has blanks.
    assert store.enrich_from_raw() == 1
    row = canonical_row()
    assert row['album'] == 'Spotify Album'
    assert row['context'] == 'spotify:playlist:abc'
    assert row['source'] == 'downtify'
    assert row['played_at'] == original_timestamp


def test_enrichment_is_idempotent_and_preserves_known_values():
    # Canonical row already has Downtify album/context.
    assert store.enrich_from_raw() == 0
    assert canonical_row()['context'] == 'Downtify Playlist'
```

Add a Spotify sweep test proving a raw row enriched after linking updates the blank canonical context through `run_once()`.

- [ ] **Step 2: Run the narrow tests and verify RED**

Run: `ssh home 'docker exec downtify-feature-py sh -lc "cd /work && uv run pytest tests/test_listening_history.py tests/test_spotify_history.py -q"'`

Expected: FAIL because `enrich_from_raw` is absent.

- [ ] **Step 3: Implement bounded fill-only enrichment**

Use keyset-paged raw rows. Parse Spotify `context_json` defensively; update canonical album/context/context type only where each target is blank. Fill blank albums from Spotify and Last.fm raw rows. Never modify source, identity, timestamp, match key or counts. Missing raw tables are a no-op. Run after bootstrap linking/activity backfill and after Spotify `link_pending()` when a listening store exists.

- [ ] **Step 4: Run the narrow suite and verify GREEN**

Run: `ssh home 'docker exec downtify-feature-py sh -lc "cd /work && uv run pytest tests/test_listening_history.py tests/test_spotify_history.py -q"'`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add downtify/listening_history.py downtify/spotify_history.py tests/test_listening_history.py tests/test_spotify_history.py
git commit -m "fix(stats): enrich historical canonical metadata safely"
```

### Task 5: Accessible, localized and gap-safe heatmap

**Files:**
- Modify: `frontend/src/lib/heatmap.js`
- Modify: `frontend/src/components/library/ActivityHeatmap.vue`
- Test: `frontend/src/__tests__/heatmap.test.js`
- Create: `frontend/src/__tests__/heatmapInteraction.test.js`

**Interfaces:**
- Consumes: existing `heatmapCells/Columns/Lead` and `selected`/`locale` props.
- Produces: `resolveHeatmapKey(event, index, count) -> {type: 'move'|'edge'|'activate', index?: number} | null`; heatmap emits unchanged `select(date)`.

- [ ] **Step 1: Write failing key-resolver tests**

```js
expect(resolveHeatmapKey({ key: 'ArrowRight' }, 10, 364)).toEqual({ type: 'move', index: 11 })
expect(resolveHeatmapKey({ key: 'ArrowDown' }, 10, 364)).toEqual({ type: 'move', index: 17 })
expect(resolveHeatmapKey({ key: 'Home' }, 10, 364)).toEqual({ type: 'edge', index: 0 })
expect(resolveHeatmapKey({ key: 'Enter' }, 10, 364)).toEqual({ type: 'activate', index: 10 })
```

Clamp moves at both edges; unrelated keys return `null`.

- [ ] **Step 2: Write failing component interaction/rendering tests**

Cover: internal-gap `mouseover` preserves hover; changed `days` updates the hovered count by date; focus moving within the grid does not clear the tooltip; SSR has exactly one `tabindex="0"`; selected markup retains `outline-accent`; tooltip has `role="tooltip"`; no `hover:outline` utility can override selection; localized play text is rendered.

- [ ] **Step 3: Run frontend tests and verify RED**

Run: `ssh home 'docker exec downtify-feature-node sh -lc "cd /work/frontend && npm test -- --run src/__tests__/heatmap.test.js src/__tests__/heatmapInteraction.test.js"'`

Expected: FAIL on missing key resolver and reproduced interaction/rendering contracts.

- [ ] **Step 4: Implement the heatmap fixes**

Store hover by date and derive the current cell from `byDate`. Ignore non-cell delegated events while inside the grid; clear only on actual leave/outside focus. Add one active tab stop, 2D key handling and DOM focus movement. Localize labels/tooltips, add tooltip/help semantics, move level/selection classes to an inner painted square, and add scoped coarse-pointer 24px targets. Keep reduced-motion rules.

- [ ] **Step 5: Run frontend tests and verify GREEN**

Run: `ssh home 'docker exec downtify-feature-node sh -lc "cd /work/frontend && npm test -- --run src/__tests__/heatmap.test.js src/__tests__/heatmapInteraction.test.js src/__tests__/statsViewClientRender.test.js"'`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/heatmap.js frontend/src/components/library/ActivityHeatmap.vue frontend/src/__tests__/heatmap.test.js frontend/src/__tests__/heatmapInteraction.test.js
git commit -m "fix(stats): make listening heatmap reliable and accessible"
```

### Task 6: Stats profile, patterns, Last.fm and background day panel

**Files:**
- Modify: `frontend/src/model/stats.js`
- Modify: `frontend/src/views/StatsView.vue`
- Modify: `frontend/src/i18n/locales/{en,tr,es,fr,hu,pt-BR,el,bg}.js`
- Test: `frontend/src/__tests__/statsPeriod.test.js`
- Test: `frontend/src/__tests__/statsViewClientRender.test.js`
- Create: `frontend/src/__tests__/statsLocale.test.js`

**Interfaces:**
- Consumes: Task 1–3 `playback` fields and Task 5 heatmap behavior.
- Produces: `load(selectedDate = '', { background = false } = {})`, `dayLoading`, `dayError`, and `playsForDay(stats, selectedDate) -> array`.

- [ ] **Step 1: Write failing model tests**

```js
await stats.load('2026-11-20', { background: true })
expect(API.getStats).toHaveBeenCalledWith({ days: 30, scope: 'user', date: '2026-11-20' })
expect(stats.loading.value).toBe(false)
expect(stats.dayLoading.value).toBe(false)

// Resolve request 2 before request 1; stats must retain request 2.
```

Add `playsForDay` assertions for no selection, selected server-day rows and missing day data.

- [ ] **Step 2: Write failing locale and client-compile tests**

Require every new Stats key in all eight locales. Keep the client-mode SFC compilation test green after template changes.

- [ ] **Step 3: Run frontend tests and verify RED**

Run: `ssh home 'docker exec downtify-feature-node sh -lc "cd /work/frontend && npm test -- --run src/__tests__/statsPeriod.test.js src/__tests__/statsViewClientRender.test.js src/__tests__/statsLocale.test.js"'`

Expected: FAIL on missing date/background/helper/locale contracts.

- [ ] **Step 4: Implement model sequencing and selected-day helper**

Add a monotonically increasing request sequence. Only the latest request may replace `stats` or set errors. Background day loads set `dayLoading/dayError` without toggling whole-page `loading/error`. Omit `date` from default requests. Add `playsForDay()`.

- [ ] **Step 5: Implement the Stats surfaces and eight locales**

Relabel measured listening; add profile cards/source bars, known-time coverage, UTC hour/weekday bars and Last.fm loved/MBID/import-state lines. Watch both period and selected day; day changes use background loading. Show exact day total, truncation note and inline retry. Use server day rows rather than filtering `recent`. Preserve v4 tokens, empty states and reduced motion.

- [ ] **Step 6: Run frontend tests/build and verify GREEN**

Run: `ssh home 'docker exec downtify-feature-node sh -lc "cd /work/frontend && npm test -- --run src/__tests__/statsPeriod.test.js src/__tests__/statsViewClientRender.test.js src/__tests__/statsLocale.test.js src/__tests__/heatmap.test.js src/__tests__/heatmapInteraction.test.js && npm run build"'`

Expected: PASS and build completes.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/model/stats.js frontend/src/views/StatsView.vue frontend/src/i18n/locales frontend/src/__tests__/statsPeriod.test.js frontend/src/__tests__/statsViewClientRender.test.js frontend/src/__tests__/statsLocale.test.js
git commit -m "feat(stats): add deep listening profile and exact-day panel"
```

### Task 7: Documentation, full gates, independent review and deploy

**Files:**
- Modify: `docs/features/stats.md`
- Modify: `docs/api-reference.md:2113-2162`

- [ ] **Step 1: Update Stats and API documentation**

Document selected-window semantics, canonical source split, known album/time coverage, UTC patterns, Last.fm loved-at-import/MBID/backfill fields, fill-only enrichment, `date`, day cap and corrected heatmap keyboard/pointer behavior. Replace the stale trend-line sentence with the block chart actually rendered.

- [ ] **Step 2: Run formatting and static checks**

Run: `ssh home 'docker exec downtify-feature-node sh -lc "cd /work/frontend && npm run format:check"'`

Run: `ssh home 'docker exec downtify-feature-py sh -lc "cd /work && uv run ruff check . && uv run ruff format --check ."'`

Run: `ssh home 'cd /home/yeet/downtify/.worktrees/personal-server-program && git diff --check'`

Expected: all clean.

- [ ] **Step 3: Run full backend/frontend/docs gates**

Run: `ssh home 'docker exec downtify-feature-py sh -lc "cd /work && uv run pytest -q"'`

Run: `ssh home 'docker exec downtify-feature-node sh -lc "cd /work/frontend && npm test"'`

Run: `ssh home 'docker exec downtify-feature-node sh -lc "cd /work/docs && npm test && npm run build"'`

Run: `ssh home 'docker exec downtify-feature-node sh -lc "cd /work/frontend && npm run build"'`

Expected: all pass; record exact counts in the commit/review notes.

- [ ] **Step 4: Commit documentation**

```bash
git add docs/features/stats.md docs/api-reference.md
git commit -m "docs(stats): document deep analytics and heatmap behavior"
```

- [ ] **Step 5: Independent review**

Dispatch a read-only reviewer using a live-verified zero-cost `opencode-go` chat model. Review the complete branch against the spec, with special attention to the five Review Focus classes. Fix any confirmed blocker with its own regression test and commit.

- [ ] **Step 6: Integrate and deploy**

Fast-forward `feat/collections` to the reviewed `feat/personal-server-program` HEAD. Run `ssh home '~/bin/downtify-deploy.sh'`. Verify `/api/health` is `{"status":"ok","version":"4.0.0"}`, the container is healthy, and live Stats contains the additive fields without changing measured seconds.

- [ ] **Step 7: Browser acceptance**

At desktop and mobile widths verify: profile/source/pattern/Last.fm panels; tooltip across gaps; one-tab-stop arrow navigation; selected ring on hover; exact-day list older than the recent page; reduced-motion static tooltip; no console errors. Record evidence and any deferred minor separately.
