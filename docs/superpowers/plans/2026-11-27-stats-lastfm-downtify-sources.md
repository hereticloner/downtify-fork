# Stats Last.fm + Downtify Sources Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Stats count only Last.fm and Downtify plays, reconcile existing merged plays to Last.fm metadata, and restore fresh recent-play imports without deleting Spotify data.

**Architecture:** Change canonical source precedence to Downtify → Last.fm → Spotify, idempotently reconcile legacy Last.fm-linked winners, and filter every Stats read to Downtify/Last.fm. Add a bounded startup provider catch-up, then simplify StatsView source presentation and document the retained Spotify archive.

**Tech Stack:** Python 3.14, FastAPI lifespan, SQLite, Vue 3, Vitest, VitePress

**Spec:** `docs/superpowers/specs/2026-11-27-stats-lastfm-downtify-sources-design.md`

## Global Constraints

- Do not delete raw Spotify rows, Spotify-only canonical rows or legacy top-level `spotify` API fields.
- Do not disable Spotify Connect, Spotify Sync or Spotify raw-history collection.
- Preserve `listening_events.id`, `identity_key` and every `listening_event_sources` link.
- `by_source` retains `spotify: 0` for API compatibility.
- Known listening seconds/completions/skips still come only from Downtify position reports.
- No new providers, dependencies, public sharing, OIDC or upstream merges.
- Preserve Technical Gazette styling, compact typography, covers, eight locales and reduced-motion behavior.
- No fuzzy title-matching expansion; exclude Spotify-only plays instead of forcing uncertain duplicates together.

## Review Focus

- A legacy Spotify winner linked to Last.fm must become Last.fm without changing event identity or source links — Task 1 reconciliation test.
- A Spotify-only event must disappear from main Stats, day detail and pattern detail, while a Downtify+Spotify event remains Downtify — Task 2 aggregate/detail tests.
- Last.fm promotion must clear Spotify duration/context so known time and provenance stay truthful — Task 1 reconciliation assertions.
- One provider catch-up failing must not fail startup or leak refreshed tokens into logs/results — Task 3 helper tests.
- Legacy fixtures/API payloads may still contain Spotify rows; StatsView must not render them, and all eight locales must describe the two-source model — Task 4 UI/locale tests.

---

### Task 1: Last.fm canonical precedence and legacy reconciliation

**Files:**
- Modify: `downtify/listening_history.py`
- Test: `tests/test_listening_history.py`
- Test: `tests/test_listening_stats_api.py`

**Interfaces:**
- Consumes: existing `ListeningStore.link_or_create()`, `lastfm_history.TABLE`, `listening_event_sources`.
- Produces: `ListeningStore.reconcile_lastfm_sources() -> int`; module priority `downtify: 0`, `lastfm: 1`, `spotify: 2`; bootstrap invokes reconciliation after raw linking.

- [ ] **Step 1: Write failing precedence and reconciliation tests**

Add `test_lastfm_promotes_spotify_and_downtify_still_wins`: create a Spotify event, link the same play from Last.fm with a different timestamp/title, assert one event whose source/time/title are Last.fm; then link Downtify and assert Downtify wins.

Add `test_reconcile_lastfm_sources_upgrades_legacy_rows_idempotently`: construct a legacy Spotify canonical row with duration/context and a linked `lastfm_recent_tracks` row. Call `reconcile_lastfm_sources()` and assert:

- return value `1`, second call `0`;
- `source='lastfm'`, `source_key/played_at/title/artist/album` come from Last.fm;
- `duration_ms=0`, `context=''`, `context_type=''`;
- `id`, `identity_key`, `match_key`, source-link rows and raw rows are unchanged.

Add `test_reconcile_lastfm_sources_keeps_downtify_links`: a Downtify+Last.fm event keeps Downtify fields and is not counted as reconciled.

- [ ] **Step 2: Run the new tests and verify RED**

Run: `.venv/bin/pytest -q tests/test_listening_history.py -k 'lastfm_promotes or reconcile_lastfm'`
Expected: FAIL because Last.fm does not yet outrank Spotify and `reconcile_lastfm_sources` does not exist.

- [ ] **Step 3: Implement precedence and reconciliation**

Change `_SOURCE_PRIORITY` to `{'downtify': 0, 'lastfm': 1, 'spotify': 2}`. Implement `reconcile_lastfm_sources()` using the linked Last.fm raw row only when the event has a Last.fm link, has no Downtify link and currently is not already an identical Last.fm winner. Update only the fields named in Step 1; preserve identity and links. Return the number of rows actually changed.

- [ ] **Step 4: Run the new tests and verify GREEN**

Run: `.venv/bin/pytest -q tests/test_listening_history.py -k 'lastfm_promotes or reconcile_lastfm'`
Expected: PASS.

- [ ] **Step 5: Add the bootstrap reconciliation regression**

Extend `tests/test_listening_stats_api.py` so `bootstrap_listening_history()` reconciles a legacy linked row after draining raw backlogs. Run it RED, add the call at the end of `bootstrap_listening_history()`, then run GREEN.

- [ ] **Step 6: Run the affected suites**

Run: `.venv/bin/pytest -q tests/test_listening_history.py tests/test_listening_stats_api.py`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add downtify/listening_history.py tests/test_listening_history.py tests/test_listening_stats_api.py
git commit -m "fix(stats): prefer Last.fm for canonical play metadata"
```

---

### Task 2: Exclude Spotify-only plays from every Stats read

**Files:**
- Modify: `downtify/listening_history.py`
- Test: `tests/test_listening_history.py`
- Test: `tests/test_api_stats.py`
- Test: `tests/test_listening_stats_api.py`

**Interfaces:**
- Consumes: `reconcile_lastfm_sources()` and canonical winners from Task 1.
- Produces: `ListeningStore.stats()`, `day_plays()` and `pattern_detail()` read only `source IN ('downtify', 'lastfm')`; all existing response keys remain.

- [ ] **Step 1: Write failing source-filter tests**

Add `test_stats_excludes_spotify_only_but_keeps_lastfm_and_downtify` with four events:

1. Spotify-only, with duration/context;
2. Last.fm-only;
3. legacy Spotify+Last.fm merged row, reconciled in the test;
4. Downtify+Spotify local play.

Assert `stats()['total'] == 3`, `profile.by_source == {'downtify': 1, 'spotify': 0, 'lastfm': 2}`, no recent/top row has source Spotify, and Spotify-only duration is absent from `track_time`.

Add `test_day_and_pattern_details_use_the_same_stats_source_filter`: put Spotify-only and Last.fm plays in the same UTC day/hour; assert `day_plays()` and `pattern_detail()` totals are `1` and contain only Last.fm.

Add a user-scope assertion: another user's Spotify-only row never enters either scope.

- [ ] **Step 2: Run the new tests and verify RED**

Run: `.venv/bin/pytest -q tests/test_listening_history.py -k 'excludes_spotify_only or same_stats_source_filter'`
Expected: FAIL because Spotify-only rows are currently counted.

- [ ] **Step 3: Apply the filter at each read boundary**

In `stats()`, `pattern_detail()` and `day_plays()`, extend the base `where` clause with `source IN ('downtify', 'lastfm')`. Also apply `e.source IN ('downtify', 'lastfm')` to the Last.fm loved/MBID detail join. Keep all three `by_source` keys; Spotify remains zero.

- [ ] **Step 4: Update existing Stats fixtures that used Spotify as a generic included source**

In `tests/test_listening_history.py` and `tests/test_api_stats.py`, change intended included Stats events from `source='spotify'` to `source='lastfm'` where the test is about offsets, windows, profile aggregates, top lists, user scope or details. Keep Spotify-specific import/idempotency/dedupe tests unchanged. Update `test_stats_counts_spotify_and_lastfm_without_faking_measured_time` to assert Spotify-only is excluded while Last.fm remains and measured time stays zero. In `tests/test_listening_stats_api.py::test_bootstrap_links_all_pending_rows_in_batches`, keep the 250 Spotify raw rows as the batch-linking fixture and change the Stats total assertion from `251` to `1`, proving the Downtify activity row remains while Spotify-only rows are excluded.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run: `.venv/bin/pytest -q tests/test_listening_history.py tests/test_api_stats.py tests/test_listening_stats_api.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add downtify/listening_history.py tests/test_listening_history.py tests/test_api_stats.py tests/test_listening_stats_api.py
git commit -m "fix(stats): count only Last.fm and Downtify plays"
```

---

### Task 3: Deterministic startup catch-up and visible refresh failures

**Files:**
- Modify: `downtify/listening_history.py`
- Modify: `downtify/spotify_history.py`
- Modify: `downtify/lastfm_history.py`
- Modify: `main.py`
- Create: `tests/test_listening_history_refresh.py`
- Test: `tests/test_spotify_history.py`

**Interfaces:**
- Consumes: existing `spotify_history.run_once()`, `lastfm_history.run_once()`, settings, `ListeningStore`.
- Produces: `async catch_up_listening_history(settings, db_path, listening, *, user_id, persist_tokens=None) -> dict[str, Any]`; lifespan awaits it before spawning periodic history loops; periodic saved/error summaries log at INFO.

- [ ] **Step 1: Write failing catch-up helper tests**

Add `test_catch_up_runs_both_providers_and_reconciles`: monkeypatch both `run_once` functions with fakes, await the helper, assert both called once with the same user id, Last.fm uses `max_pages=1`, Spotify results exclude `tokens`, and reconciliation runs once.

Add `test_catch_up_persists_spotify_token_renewal_without_returning_it`: fake Spotify returns a `tokens` dict; assert the callback receives it and the returned summary contains no token values.

Add `test_catch_up_isolates_provider_failure`: one fake raises; assert the other result remains, the failed provider returns only an error type, and no exception escapes.

- [ ] **Step 2: Run the new tests and verify RED**

Run: `.venv/bin/pytest -q tests/test_listening_history_refresh.py`
Expected: FAIL because `catch_up_listening_history` does not exist.

- [ ] **Step 3: Implement the helper**

Run both provider `run_once` calls concurrently with `asyncio.to_thread` and `asyncio.gather(return_exceptions=True)`. Persist Spotify renewal through the callback, remove `tokens` before returning/logging, convert provider exceptions to `{'error': type(exc).__name__}`, then call `listening.reconcile_lastfm_sources()` and include its count as `reconciled`.

- [ ] **Step 4: Run the helper tests and verify GREEN**

Run: `.venv/bin/pytest -q tests/test_listening_history_refresh.py`
Expected: PASS.

- [ ] **Step 5: Wire startup and improve periodic logging**

In `main.py` lifespan, await one catch-up immediately before the `spotify-history-loop` and `lastfm-history-loop` tasks are spawned. Pass `api.state.settings`, the activity DB, `api.state.listening`, the first-admin id and `api._persist_mirror_tokens`; wrap it so provider failure cannot fail startup; log only the redacted summary. In both periodic loops, change saved/error messages from DEBUG to INFO while keeping empty success quiet.

- [ ] **Step 6: Update stale Spotify-history Stats assertions and run affected checks**

In `tests/test_spotify_history.py::test_raw_payload_and_pending_link_are_idempotent` and `::test_run_once_links_imported_play_to_canonical_history`, keep proving the Spotify raw/canonical import landed, but assert `listening.stats(user_id=1)['total'] == 0`; add a direct canonical-row count assertion of `1` so the import behavior remains covered.

Run: `.venv/bin/pytest -q tests/test_listening_history_refresh.py tests/test_spotify_history.py tests/test_lastfm_history.py tests/test_startup_backfill.py`
Expected: PASS.

Run: `.venv/bin/ruff check downtify/listening_history.py downtify/spotify_history.py downtify/lastfm_history.py main.py tests/test_listening_history_refresh.py tests/test_spotify_history.py`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add downtify/listening_history.py downtify/spotify_history.py downtify/lastfm_history.py main.py tests/test_listening_history_refresh.py tests/test_spotify_history.py
git commit -m "fix(stats): catch up listening history on startup"
```

---

### Task 4: Two-source Stats UI, locale copy and current documentation

**Files:**
- Modify: `frontend/src/views/StatsView.vue`
- Modify: `frontend/src/__tests__/listeningSources.test.js`
- Modify: `frontend/src/__tests__/pageHeader.test.js`
- Modify: `frontend/src/__tests__/statsLocale.test.js`
- Modify: `frontend/src/i18n/locales/{en,tr,es,fr,pt-BR,hu,el,bg}.js`
- Modify: `docs/features/stats.md`
- Modify: `docs/api-reference.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: filtered Stats API from Task 2; legacy payloads may still contain Spotify rows.
- Produces: StatsView renders only Downtify/Last.fm source rows and badges, defensively drops Spotify recent rows, and all locale copy describes Last.fm + Downtify.

- [ ] **Step 1: Write failing UI and locale tests**

Update `listeningSources.test.js` to keep a legacy Spotify recent row in the fixture but assert it is not rendered; assert Downtify/Last.fm badges and the filtered API total remain. Update `pageHeader.test.js` to use Last.fm recent/source counts, assert `stats.sourceSpotify` is absent from rendered Stats, and assert Downtify is the solid source row. Extend `statsLocale.test.js` to assert every locale's `stats.sourcePriority` excludes Spotify and includes `Downtify → Last.fm`, and every `settings.spotifyMirrorImportHint` says Spotify history is stored separately from Stats.

- [ ] **Step 2: Run the tests and verify RED**

Run: `npm test -- --run src/__tests__/listeningSources.test.js src/__tests__/pageHeader.test.js src/__tests__/statsLocale.test.js`
Expected: FAIL on Spotify rendering and old locale copy.

- [ ] **Step 3: Implement the two-source presentation**

Change `sourceRows()` to `['downtify', 'lastfm']`, filter `recentRows` to exclude `source === 'spotify'`, and make the Downtify source bar use `bg-fg` while Last.fm remains `bg-surface-2`. Keep the Spotify translation keys for parity/compatibility.

Replace `Downtify → Spotify → Last.fm` with `Downtify → Last.fm` in all eight `sourcePriority` strings. Update `spotifyMirrorImportHint` with the exact meanings below, preserving the reconnect/scope warning:

| Locale | New hint |
|---|---|
| en | Store your Spotify listening history separately every half hour. Stats uses Last.fm + Downtify. Needs one reconnect so Spotify grants the scope. |
| tr | Spotify dinleme geçmişini her yarım saatte ayrı olarak sakla. Stats Last.fm + Downtify kullanır. Spotify’in izni vermesi için bir kez yeniden bağlantı gerekir. |
| es | Guarda tu historial de escuchas de Spotify por separado cada media hora. Stats usa Last.fm + Downtify. Requiere una reconexión para que Spotify conceda el permiso. |
| fr | Enregistrez séparément votre historique d’écoute Spotify toutes les demi-heures. Stats utilise Last.fm + Downtify. Une reconnexion est nécessaire pour que Spotify accorde l’autorisation. |
| pt-BR | Salve seu histórico de reproduções do Spotify separadamente a cada meia hora. As estatísticas usam Last.fm + Downtify. É necessário reconectar para o Spotify conceder a permissão. |
| hu | A Spotify hallgatási előzményeit félóránként külön tárolja. A Stats a Last.fm + Downtify forrásait használja. A Spotify engedélyezéséhez egyszeri újracsatlakozás szükséges. |
| el | Αποθηκεύστε χωριστά το ιστορικό ακρόασης Spotify κάθε μισή ώρα. Τα Stats χρησιμοποιούν Last.fm + Downtify. Απαιτείται μια επανασύνδεση για να παραχωρήσει άδεια το Spotify. |
| bg | Запазва историята на слушането в Spotify отделно на всеки половин час. Stats използва Last.fm + Downtify. Нужно е еднократно повторно свързване, за да разреши Spotify. |

- [ ] **Step 4: Update current docs**

In `README.md`, change the feature-list phrase “unified Downtify/Spotify/Last.fm play history” to a Last.fm + Downtify Stats profile and keep the existing link to `docs/features/stats.md`. In `docs/features/stats.md` and `docs/api-reference.md`, state that Stats counts Downtify + Last.fm only; Spotify raw/legacy fields remain but are not Stats sources; precedence is Downtify → Last.fm → Spotify for canonical reconciliation; Spotify-only rows are excluded from all Stats aggregates/details; startup catches up new provider pages; and `by_source.spotify` stays zero. Replace stale examples with a clearly illustrative two-source payload (for example total `3`, `downtify: 1`, `lastfm: 2`, `spotify: 0`) rather than claiming unmeasured live totals. Leave historical superpowers specs/plans unchanged.

- [ ] **Step 5: Run frontend/docs gates**

Run: `npm test && npm run build` in `frontend/`
Expected: PASS.

Run: `npm test && npm run build` in `docs/`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/StatsView.vue frontend/src/__tests__/listeningSources.test.js frontend/src/__tests__/pageHeader.test.js frontend/src/__tests__/statsLocale.test.js frontend/src/i18n/locales docs/features/stats.md docs/api-reference.md README.md
git commit -m "fix(stats): show only Last.fm and Downtify sources"
```

---

### Final verification and deployment

- [ ] Run `.venv/bin/pytest -q`, `.venv/bin/ruff check .`, frontend `npm test && npm run build`, docs `npm test && npm run build`, and `git diff --check` on the merged HEAD.
- [ ] Create a verified host bundle, fast-forward `feat/collections`, tag the rollback image, and deploy with `~/bin/downtify-deploy.sh`.
- [ ] Before deploy, back up `docker/data/settings.json`, change its owner to the Downtify process UID/GID (`1000:1000`), and verify the container process can write it. Do not print file contents or tokens.
- [ ] In the live container, call `ListeningStore.stats(user_id=1)` and assert: `profile.by_source['spotify'] == 0`; no `recent` row has Spotify source; newest local `played_at` matches the provider's newest play within one import interval; Spotify-only raw/canonical rows still exist.
- [ ] Verify `/` 200, health `ok` / 4.0.0, container healthy, new Stats asset loaded, no settings persistence warning after token renewal, and no background test servers/processes remain.
- [ ] Push `feat/collections` to GitHub only after live verification; confirm with `ls-remote`. Update vault memory/project/knowledge notes and ship the vault.
