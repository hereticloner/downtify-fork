# Stats Context Names + Interactive Patterns Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace raw Spotify context URIs with cached live names or localized type fallbacks, and make UTC Listening Patterns bars keyboard/pointer interactive with exact bucket drilldown.

**Architecture:** Add a persistent `spotify_context_cache` and background resolver that uses the existing mirror OAuth token while Stats GETs remain cache-only. Add an additive period-scoped `pattern_detail` query over canonical `listening_events`, then expose it through a focused Vue Patterns component and detail panel with stale-response protection.

**Tech Stack:** Python/FastAPI/SQLite/httpx, Vue 3/Vite/Vitest, existing i18n and Tailwind tokens; no new dependencies.

**Spec:** `docs/superpowers/specs/2026-11-26-stats-context-patterns-design.md`

## Global Constraints

- Work in `/home/yeet/downtify/.worktrees/personal-server-program` on `feat/personal-server-program`; preserve v4 identity, reduced motion, eight locales, API compatibility and port `8000`.
- Canonical play counts come only from `listening_events`; raw provider rows remain provenance.
- Selected windows and buckets are UTC: today plus the preceding `days - 1` days; `days` is `7`, `30` or `90`.
- Stats GET never calls Spotify. Live resolution is bounded, background-only and best-effort.
- Existing response fields keep their meaning; new fields are additive.
- No new dependency, audio provider, OIDC, PostgreSQL, public sharing or upstream merge.
- Test-first, separate commits, independent whole-branch review, fast-forward merge to `feat/collections`, verified deploy.

## Review Focus

- **Spotify failure modes:** offline, 401/403, 404, 429, malformed body and private resources must keep Stats available and show a truthful fallback label.
- **Canonical consistency:** bucket detail totals must equal bar counts; multi-source observations count once and source split uses canonical winners.
- **UTC edges:** midnight, last second, offset timestamps and weekday/hour boundaries must land in the intended bucket.
- **Selection races:** rapid period/day/pattern changes must not apply stale responses or show two conflicting drilldown scopes.
- **Context coverage:** URI/URL/legacy forms normalize correctly, and detail-only contexts receive labels without leaking raw URIs as primary text.

## File Structure

- `downtify/spotify_context.py` — context parsing/normalization, cache schema/read/write, background resolver and loop.
- `downtify/listening_history.py` — exact period-scoped pattern detail over canonical events.
- `downtify/stats.py` — additive pattern-detail response shaping.
- `downtify/collections_api.py` — query validation, cache-only context labels and response plumbing.
- `downtify/backup.py` — context-cache backup/restore registration.
- `main.py` — schema setup and background resolver task.
- `frontend/src/lib/context.js` — pure context display fallback.
- `frontend/src/lib/pattern.js` — pure 1D key/share helpers.
- `frontend/src/components/library/ListeningPatterns.vue` — accessible interactive charts.
- `frontend/src/model/stats.js` — pattern/day background state, request sequencing and field merges.
- `frontend/src/views/StatsView.vue` — context labels, Patterns component and detail panel.
- Eight locale files — context and pattern strings.
- `tests/test_spotify_context.py`, `tests/test_listening_history.py`, `tests/test_api_stats.py`, `tests/test_backup.py` — backend contracts.
- `frontend/src/__tests__/contextLabel.test.js`, `statsPattern.test.js`, `statsPeriod.test.js`, `statsLocale.test.js`, `statsViewClientRender.test.js` — frontend contracts.
- `docs/features/stats.md`, `docs/api-reference.md` — user/API truth.

---

### Task 0: Commit the approved design and plan

**Files:**
- Create: `docs/superpowers/specs/2026-11-26-stats-context-patterns-design.md`
- Create: `docs/superpowers/plans/2026-11-26-stats-context-patterns.md`

- [ ] Confirm the design status is `Approved — implementation authorized`.
- [ ] Confirm no production files are modified.
- [ ] Commit both documents as `docs(stats): approve context names and patterns design`.

### Task 1: Spotify context parser, cache and cache-only labels

**Files:**
- Create: `downtify/spotify_context.py`
- Create: `tests/test_spotify_context.py`
- Modify: `downtify/collections_api.py:339-465`
- Modify: `downtify/backup.py:40-95`
- Test: `tests/test_api_stats.py`
- Test: `tests/test_backup.py`

**Interfaces:**
- Produces: `ensure_schema(db_path)`, `normalize_context(value) -> str`, `context_kind(value) -> str`, `cache_name(db_path, context_key, name) -> None`, `labels_for(db_path, values) -> dict[str, str]`.

- [ ] **Write failing parser/cache tests**

```python
def test_normalize_context_accepts_supported_spotify_forms():
    assert normalize_context('spotify:playlist:abc') == 'spotify:playlist:abc'
    assert (
        normalize_context('spotify:user:u:playlist:abc')
        == 'spotify:playlist:abc'
    )
    assert (
        normalize_context('https://open.spotify.com/playlist/abc?si=x')
        == 'spotify:playlist:abc'
    )
    assert (
        normalize_context('https://api.spotify.com/v1/artists/abc')
        == 'spotify:artist:abc'
    )
    assert normalize_context('Downtify Playlist') == ''


def test_labels_for_returns_only_cached_nonempty_names(tmp_path):
    ensure_schema(db)
    cache_name(db, 'spotify:playlist:abc', 'Cached Playlist')
    assert labels_for(
        db, ['spotify:playlist:abc', 'spotify:artist:missing']
    ) == {'spotify:playlist:abc': 'Cached Playlist'}
```

- [ ] **Run tests and verify RED**

Run: `ssh home 'docker exec downtify-feature-py sh -lc "cd /work && uv run pytest tests/test_spotify_context.py -q"'`

Expected: FAIL because the module/label field/cache table do not exist.

- [ ] **Implement schema, normalization and cache reads**

Create the table from the spec. Provide `cache_name()` for later resolver use. Unknown/non-Spotify values normalize to `''`. Cache reads tolerate a missing table/database and return only non-empty names.

- [ ] **Write failing endpoint/backup tests**

```python
def test_stats_context_labels_are_cache_only(client):
    # Seed cache directly; monkeypatch Spotify transport to explode if called.
    data = client.get('/api/stats').json()['playback']
    assert data['context_labels']['spotify:playlist:abc'] == 'Cached Playlist'
```

Assert empty-activity returns `context_labels: {}` and backup table/key lists include `spotify_context_cache`.

- [ ] **Run endpoint/backup tests and verify RED**

Run: `ssh home 'docker exec downtify-feature-py sh -lc "cd /work && uv run pytest tests/test_api_stats.py::test_stats_context_labels_are_cache_only tests/test_backup.py -q"'`

Expected: FAIL on missing response key/backup registration.

- [ ] **Implement endpoint label gathering and backup registration**

After `build_stats()`, gather contexts from `top_contexts`, `recent`, `day.plays` and later `pattern_detail.recent`; call `labels_for()` without network. Add the cache table and `context_key` primary key to backup metadata. Add `{}` to the activity-none fallback.

- [ ] **Run narrow suite and verify GREEN**

Run: `ssh home 'docker exec downtify-feature-py sh -lc "cd /work && uv run pytest tests/test_spotify_context.py tests/test_api_stats.py tests/test_backup.py -q"'`

Expected: PASS.

- [ ] **Commit**

```bash
git add downtify/spotify_context.py downtify/collections_api.py downtify/backup.py tests/test_spotify_context.py tests/test_api_stats.py tests/test_backup.py
git commit -m "feat(stats): add Spotify context name cache"
```

### Task 2: Background live Spotify name resolver

**Files:**
- Modify: `downtify/spotify_context.py`
- Modify: `main.py:730-800`
- Create: `tests/test_spotify_context_resolver.py`

**Interfaces:**
- Consumes: Task 1 cache/parser and existing `spotify_mirror.ensure_token`, `_bearer`, `SPOTIFY_API`.
- Produces: `run_once(settings, db_path, *, limit=25, request=None) -> dict`; `spotify_context_loop(cfg_getter, db_path, *, idle_seconds=900, limit=25, request=None, persist_tokens=None)`; renewed-token callback compatibility.

- [ ] **Write failing resolver tests**

```python
def test_resolver_uses_existing_token_and_caches_name():
    summary = run_once(settings, db, request=fake_request)
    assert summary['resolved'] == 1
    assert (
        labels_for(db, ['spotify:playlist:abc'])['spotify:playlist:abc']
        == 'Real Playlist'
    )


def test_resolver_stops_on_429_and_honors_retry_after():
    summary = run_once(settings, db, request=rate_limited)
    assert summary['rate_limited'] is True
    assert summary['retry_after'] == 12
```

Add 401/403, 404, malformed JSON, stale-name refresh, oldest-first ordering and token-renewal persistence tests. Assert Stats/cache reads make no provider calls.

- [ ] **Run tests and verify RED**

Run: `ssh home 'docker exec downtify-feature-py sh -lc "cd /work && uv run pytest tests/test_spotify_context_resolver.py -q"'`

Expected: FAIL because resolver functions do not exist.

- [ ] **Implement bounded resolution and loop wiring**

Queue distinct canonical contexts with a Spotify source link, normalized and ordered by `MIN(played_at)`. Resolve at most 25 per pass, space calls by one second, refresh successful names after 30 days, retry errors after six hours and 404 after 24 hours. Stop on 401/403/429; honor `Retry-After`. Run when mirror is enabled with client id and access/refresh token, independent of device id and `import_recent`. Spawn the loop in `main.py` and pass the existing token persistence callback.

- [ ] **Run narrow suite and verify GREEN**

Run: `ssh home 'docker exec downtify-feature-py sh -lc "cd /work && uv run pytest tests/test_spotify_context_resolver.py tests/test_spotify_context.py -q"'`

Expected: PASS.

- [ ] **Commit**

```bash
git add downtify/spotify_context.py main.py tests/test_spotify_context_resolver.py
git commit -m "feat(stats): resolve Spotify context names in background"
```

### Task 3: Exact pattern-detail API

**Files:**
- Modify: `downtify/listening_history.py`
- Modify: `downtify/stats.py`
- Modify: `downtify/collections_api.py:339-465`
- Test: `tests/test_listening_history.py`
- Test: `tests/test_api_stats.py`

**Interfaces:**
- Produces: `ListeningStore.pattern_detail(user_id, days, kind, bucket, *, top_limit=5, recent_limit=50) -> dict`; `GET /api/stats?pattern=hour|weekday&bucket=N`; additive `playback.pattern_detail`.

- [ ] **Write failing store/API tests**

```python
def test_pattern_detail_matches_hour_bar_and_uses_canonical_sources():
    detail = store.pattern_detail(1, 7, 'hour', 14)
    assert detail['total'] == store.stats(1, days=7)['patterns']['by_hour'][14]
    assert detail['by_source'] == {'downtify': 0, 'spotify': 2, 'lastfm': 0}


def test_stats_pattern_query_validates_kind_and_bucket(client):
    assert (
        client.get(
            '/api/stats', params={'pattern': 'hour', 'bucket': 24}
        ).status_code
        == 400
    )
    assert (
        client.get('/api/stats', params={'pattern': 'hour'}).status_code == 400
    )
```

Add weekday, UTC boundary, scope, cap/truncation, empty shape and context-label coverage for detail-only rows.

- [ ] **Run tests and verify RED**

Run: `ssh home 'docker exec downtify-feature-py sh -lc "cd /work && uv run pytest tests/test_listening_history.py tests/test_api_stats.py -q"'`

Expected: FAIL because `pattern_detail` and query parameters do not exist.

- [ ] **Implement the exact bucket query**

Reuse the canonical selected-window predicate and `strftime` bucket expression. Return total, canonical source split, top five tracks/artists and up to 50 newest plays with `truncated`. Validate paired parameters and ranges in the endpoint. Add empty fallback shape and include pattern-detail contexts in `context_labels`.

- [ ] **Run narrow suite and verify GREEN**

Run: `ssh home 'docker exec downtify-feature-py sh -lc "cd /work && uv run pytest tests/test_listening_history.py tests/test_api_stats.py -q"'`

Expected: PASS.

- [ ] **Commit**

```bash
git add downtify/listening_history.py downtify/stats.py downtify/collections_api.py tests/test_listening_history.py tests/test_api_stats.py
git commit -m "feat(stats): add exact listening pattern detail"
```

### Task 4: Human-readable context labels in existing Stats surfaces

**Files:**
- Create: `frontend/src/lib/context.js`
- Create: `frontend/src/__tests__/contextLabel.test.js`
- Modify: `frontend/src/views/StatsView.vue`
- Modify: `frontend/src/i18n/locales/{en,tr,es,fr,hu,pt-BR,el,bg}.js`
- Test: `frontend/src/__tests__/statsLocale.test.js`
- Test: `frontend/src/__tests__/statsViewClientRender.test.js`

**Interfaces:**
- Consumes: `playback.context_labels`.
- Produces: `spotifyContextKind(value) -> string`; `contextLabel(value, labels, t) -> string`.

- [ ] **Write failing formatter/render tests**

```js
expect(contextLabel('spotify:playlist:abc', { 'spotify:playlist:abc': 'Real Playlist' }, t)).toBe('Real Playlist')
expect(contextLabel('spotify:artist:abc', {}, t)).toBe(t('stats.contextSpotifyArtist'))
expect(contextLabel('Downtify Playlist', {}, t)).toBe('Downtify Playlist')
```

Add SSR assertions that **Most played from** and recent context badges use the resolved/fallback label, never the raw URI as primary text.

- [ ] **Run frontend tests and verify RED**

Run: `ssh home 'docker exec downtify-feature-node sh -lc "cd /work/frontend && npm test -- --run src/__tests__/contextLabel.test.js src/__tests__/statsLocale.test.js src/__tests__/statsViewClientRender.test.js"'`

Expected: FAIL on missing helper/locale keys/raw rendering.

- [ ] **Implement the shared formatter and locale keys**

Resolved cache name wins; recognized Spotify URI/URL forms fall back to localized playlist/artist/album labels; non-Spotify text passes through. Apply it to top contexts and all recent/day badges. Keep raw URI only in the API.

- [ ] **Run frontend tests and verify GREEN**

Run: `ssh home 'docker exec downtify-feature-node sh -lc "cd /work/frontend && npm test -- --run src/__tests__/contextLabel.test.js src/__tests__/statsLocale.test.js src/__tests__/statsViewClientRender.test.js"'`

Expected: PASS.

- [ ] **Commit**

```bash
git add frontend/src/lib/context.js frontend/src/views/StatsView.vue frontend/src/i18n/locales frontend/src/__tests__/contextLabel.test.js frontend/src/__tests__/statsLocale.test.js frontend/src/__tests__/statsViewClientRender.test.js
git commit -m "fix(stats): show human-readable Spotify context labels"
```

### Task 5: Interactive Patterns component, model and detail panel

**Files:**
- Create: `frontend/src/lib/pattern.js`
- Create: `frontend/src/components/library/ListeningPatterns.vue`
- Create: `frontend/src/__tests__/statsPattern.test.js`
- Modify: `frontend/src/model/stats.js`
- Modify: `frontend/src/views/StatsView.vue`
- Modify: `frontend/src/i18n/locales/*.js`
- Test: `frontend/src/__tests__/statsPeriod.test.js`
- Test: `frontend/src/__tests__/statsLocale.test.js`
- Test: `frontend/src/__tests__/statsViewClientRender.test.js`

**Interfaces:**
- Consumes: Task 3 `playback.pattern_detail` and `context_labels`.
- Produces: `resolvePatternKey(event,index,count)`; `ListeningPatterns` emits `select({kind,bucket})`; `loadPattern(kind,bucket)`; `patternLoading`, `patternError`.

- [ ] **Write failing key/model/component tests**

```js
expect(resolvePatternKey({key:'ArrowRight'}, 0, 24)).toEqual({type:'move', index:1})
expect(resolvePatternKey({key:'End'}, 0, 24)).toEqual({type:'edge', index:23})

await stats.loadPattern('hour', 14)
expect(API.getStats).toHaveBeenCalledWith({days:30, scope:'user', pattern:'hour', bucket:14})
expect(stats.patternLoading.value).toBe(false)
```

Add stale pattern response, background error isolation, field-merge, one-tab-stop SSR, selected outline, tooltip semantics, reduced-motion source contract and day/pattern mutual-exclusion tests.

- [ ] **Run frontend tests and verify RED**

Run: `ssh home 'docker exec downtify-feature-node sh -lc "cd /work/frontend && npm test -- --run src/__tests__/statsPattern.test.js src/__tests__/statsPeriod.test.js src/__tests__/statsLocale.test.js src/__tests__/statsViewClientRender.test.js"'`

Expected: FAIL on missing component/helper/model state/locale keys.

- [ ] **Implement model sequencing and field merges**

Add pattern state and a global request sequence. Foreground period loads replace Stats and invalidate detail requests. Background day/pattern loads merge only `day`/`pattern_detail` plus `context_labels`, never the whole object. Errors stay in their own state.

- [ ] **Implement the Patterns component and detail panel**

Create 1D roving button charts with tooltip count/share, selected accent, coarse-pointer 24px targets and reduced-motion handling. Add the detail panel with exact total, source split, top tracks/artists, capped recent plays, truncation, skeleton, retry, empty and clear states. Selecting a day clears pattern; selecting a pattern clears day. Period changes preserve selection and reload detail.

- [ ] **Add locale keys and run GREEN/build**

Run: `ssh home 'docker exec downtify-feature-node sh -lc "cd /work/frontend && npx prettier --write src/lib/pattern.js src/components/library/ListeningPatterns.vue src/model/stats.js src/views/StatsView.vue src/__tests__/statsPattern.test.js src/__tests__/statsPeriod.test.js src/__tests__/statsLocale.test.js src/i18n/locales/*.js && npm test -- --run src/__tests__/statsPattern.test.js src/__tests__/statsPeriod.test.js src/__tests__/statsLocale.test.js src/__tests__/statsViewClientRender.test.js src/__tests__/contextLabel.test.js && npm run build"'`

Expected: PASS and build completes.

- [ ] **Commit**

```bash
git add frontend/src/lib/pattern.js frontend/src/components/library/ListeningPatterns.vue frontend/src/model/stats.js frontend/src/views/StatsView.vue frontend/src/i18n/locales frontend/src/__tests__/statsPattern.test.js frontend/src/__tests__/statsPeriod.test.js frontend/src/__tests__/statsLocale.test.js frontend/src/__tests__/statsViewClientRender.test.js
git commit -m "feat(stats): add interactive listening pattern drilldown"
```

### Task 6: Documentation, full gates, independent review and deploy

**Files:**
- Modify: `docs/features/stats.md`
- Modify: `docs/api-reference.md:2190-2240`

- [ ] **Update Stats/API docs**

Document live best-effort names, fallback labels, cache-only GET behavior, resolver cadence/limits, `context_labels`, `pattern`/`bucket`, exact detail caps, UTC semantics and day/pattern mutual exclusion.

- [ ] **Run static checks**

Run: `ssh home 'docker exec downtify-feature-py sh -lc "cd /work && uv run ruff check . && uv run ruff format --check ."'`

Run targeted Prettier on every changed frontend file; the repository-wide check has eight known pre-existing unrelated failures.

Run: `ssh home 'cd /home/yeet/downtify/.worktrees/personal-server-program && git diff --check'`

Expected: clean.

- [ ] **Run full gates serially**

Run: `ssh home 'docker exec downtify-feature-py sh -lc "cd /work && uv run pytest -q"'`

Run: `ssh home 'docker exec downtify-feature-node sh -lc "cd /work/frontend && npm test"'`

Run: `ssh home 'docker exec downtify-feature-node sh -lc "cd /work/docs && npm test && npm run build"'`

Run: `ssh home 'docker exec downtify-feature-node sh -lc "cd /work/frontend && npm run build"'`

Expected: all pass; record exact counts.

- [ ] **Commit docs**

```bash
git add docs/features/stats.md docs/api-reference.md
git commit -m "docs(stats): document context names and pattern drilldown"
```

- [ ] **Independent review**

Dispatch a read-only reviewer using a live-verified zero-cost `opencode-go` model. Review against the spec and Review Focus. Fix Critical/Important findings with RED→GREEN tests; ledger minors.

- [ ] **Integrate, deploy and verify**

Fast-forward `feat/collections`, run `ssh home '~/bin/downtify-deploy.sh'`, verify health `ok` / `4.0.0`, additive fields, cache table in backups, fallback labels before resolution and resolved names after a resolver pass. Browser-check desktop/mobile, keyboard-only Patterns, reduced motion and Spotify-failure fallback.
