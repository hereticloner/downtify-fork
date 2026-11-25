# Lyrics Health and Sync Offset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add LRCLIB search fallback, a synced-only lyrics mode, an admin bulk lyrics-health scan/fill flow, and a device-local ±0.5-second lyrics offset without rewriting existing audio formats unnecessarily.

**Architecture:** Extend the existing lyrics provider/fetch layer and reuse `read_track_lyrics`/`write_to_file`. A focused scanner compares fresh disk files with their saved lyrics; a small admin router fills explicitly selected files in bounded batches. The player stores its offset in the user's preferences under a stable browser device ID, so it is device-specific and included in the existing user backup.

**Tech Stack:** Python 3.12+, FastAPI, SQLite, Mutagen, httpx, Vue 3, Axios, Vitest, Vite.

**Spec:** `docs/superpowers/specs/2026-11-24-personal-server-feature-program-design.md` §6.10, §6.14 and Faz 10.

## Global Constraints

- Existing MP3/FLAC/M4A/Opus tag and `.lrc` write behavior stays compatible.
- No audio file is changed by a scan; filling requires an explicit admin request.
- Offset is keyed by a stable browser device ID in user preferences, never written to the audio file or LRC sidecar, and therefore included in the existing user backup.
- New Kugou source is not added in this wave: its public endpoints are undocumented, change frequently, and carry copyright/region risk; document the evaluation.
- Preserve v4 identity, reduced-motion behavior, API compatibility, eight locales and port `8000`.
- LRCLIB requests remain sequential and honor current API guidance; bulk fill pauses 250 ms between tracks.
- No new dependency.

## Review Focus

- LRCLIB `/get` miss falls back to `/search` and never accepts a wrong title/artist just because lyrics exist.
- Synced-only mode skips plain-only provider hits, continues the chain, and writes nothing when no timed lyrics are found.
- Bulk scan is read-only; bulk fill only touches safe library paths explicitly sent by an admin and rechecks current lyrics before writing.
- A fill batch is bounded, survives per-track provider/write failures, and reports counts without exposing secrets.
- Offset clamps to ±0.5 s, changes highlighting and line-click seek consistently, persists per browser, and never mutates files.
- Existing settings/files without the new key keep their old behavior.

---

### Task 1: LRCLIB search fallback and synced-only mode

**Files:**
- Modify: `downtify/lyrics.py`
- Modify: `downtify/downloader.py`
- Modify: `downtify/api.py`
- Modify: `downtify/library_upgrade.py`
- Modify: `downtify/external_library.py`
- Modify: `frontend/src/model/settings.js`
- Modify: `frontend/src/views/SettingsView.vue`
- Modify: all eight `frontend/src/i18n/locales/*.js`
- Test: `tests/test_lyrics_providers.py`
- Test: `tests/test_downloader.py`
- Test: `tests/test_library_upgrade.py`
- Test: `tests/test_external_library.py`
- Test: `frontend/src/__tests__/settingsExtras.test.js`

**Interfaces:**
- Produces: `lyrics.fetch(song, providers, cache=None, *, synced_only=False) -> Optional[Lyrics]`.
- Produces: setting `lyrics_synced_only: bool`, default `False`.
- `Downloader.lyrics_synced_only` defaults to `False`; main and settings updates keep it in sync.

- [ ] **Step 1: Write failing provider tests**

Add to `tests/test_lyrics_providers.py`:

- `test_lrclib_search_fallback_uses_best_record`: monkeypatch `httpx.get` so `/api/get` returns 404 and `/api/search` returns a wrong-artist row plus an exact title/artist/duration row; `_fetch_lrclib` returns the exact row's synced lyrics.
- `test_lrclib_search_fallback_rejects_wrong_match`: search returns only a different title/artist; result is `None`.
- `test_synced_only_skips_plain_hit_and_uses_next_provider`: first provider returns `Lyrics(plain='words')`, second returns timed lyrics; `fetch(..., synced_only=True)` returns the second and asks both.
- `test_synced_only_returns_none_when_all_plain`: all providers return plain lyrics; result is `None`.
- `test_plain_only_still_accepts_plain_by_default`: existing behavior remains.

Add a downloader test proving `Downloader(..., lyrics_synced_only=True)` passes the flag into `lyrics.fetch`.

- [ ] **Step 2: Run tests and verify RED**

Run: `docker exec downtify-feature-py uv run pytest tests/test_lyrics_providers.py tests/test_downloader.py -q`
Expected: missing fallback/flag failures.

- [ ] **Step 3: Implement fallback and setting**

In `lyrics.py`, keep `/api/get` first. On 404, call `/api/search` with `track_name`, `artist_name`, and optional `album_name`; score normalized title/artist equality, then duration closeness. Reject candidates with neither title nor artist alignment. Parse the chosen record through the existing plain/synced extraction.

Extend `fetch` with keyword-only `synced_only=False`. A plain-only result counts as a miss when true: record the cache miss and continue. Cache hits and timed results behave as before.

Add `lyrics_synced_only=False` to `DEFAULT_SETTINGS`, coerce it in the settings save handler, pass it into `Downloader`, update `downloader.lyrics_synced_only` when saved, and forward it from `_MetadataLookups` to `fetch`.

Add the default to the frontend settings model and a **Synced lyrics only** switch under the existing lyrics settings. Add matching keys to all eight locales.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `docker exec downtify-feature-py uv run pytest tests/test_lyrics_providers.py tests/test_downloader.py -q && docker exec downtify-feature-node npm --prefix frontend test -- --maxWorkers=1 src/__tests__/settingsExtras.test.js src/__tests__/i18nParity.test.js`
Expected: all pass.

- [ ] **Step 5: Lint and commit**

```bash
git add downtify/lyrics.py downtify/downloader.py downtify/api.py main.py downtify/library_upgrade.py downtify/external_library.py frontend/src/model/settings.js frontend/src/views/SettingsView.vue frontend/src/i18n/locales tests/test_lyrics_providers.py tests/test_downloader.py tests/test_api_settings.py tests/test_library_upgrade.py tests/test_external_library.py frontend/src/__tests__/settingsExtras.test.js
git commit -m "feat(lyrics): add search fallback and synced-only mode"
```

---

### Task 2: Read-only health scan and bounded fill API

**Files:**
- Create: `downtify/lyrics_health.py`
- Create: `downtify/lyrics_health_api.py`
- Create: `tests/test_lyrics_health.py`
- Create: `tests/test_api_lyrics_health.py`
- Modify: `main.py`
- Modify: `downtify/auth.py`

**Interfaces:**
- Produces: `scan_lyrics_health(ctx, track_index=None) -> dict[str, Any]`.
- Produces: `fill_lyrics(files, ctx, settings, cache, track_index=None) -> dict[str, Any]`.
- Report: `{version, scanned_at, summary: {tracks, synced, plain_only, missing}, findings: [{file, status, title, artist, album, duration, spotify_id}], sources: {disk}, warnings: [code], synced_only: bool}`.
- Fill result: `{requested, found, written, skipped, failed, errors: [{file, code}]}`.
- Endpoints: admin-only `GET /api/lyrics/health` and `POST /api/lyrics/health/fill`.
- Fill body: `{files: [stored path, ...]}`, maximum 100 paths per request.

- [ ] **Step 1: Write failing scanner/fill tests**

Add `tests/test_lyrics_health.py`:

- `test_scan_classifies_synced_plain_and_missing`: three fake audio files with timed sidecar, embedded plain tag, and no lyrics; summary and statuses match.
- `test_scan_is_read_only`: hash file bytes, sidecar bytes and store rows before/after two scans.
- `test_scan_uses_fresh_disk_snapshot`: remove a file after seeding and observe `missing`/index behavior without relying on the warm listing cache.
- `test_scan_missing_root_is_partial`: a missing downloads root yields `sources.disk=false` and `disk_unavailable`, not a healthy empty report.
- `test_fill_skips_already_synced_and_rejects_outside_paths`: send one safe missing file plus `../secret.mp3`; only the safe file is considered and traversal is reported as failed.
- `test_fill_writes_only_after_explicit_request`: monkeypatch provider fetch/write and assert scan alone never calls them; fill calls once and returns `written=1`.
- `test_fill_continues_after_one_failure`: first provider/write raises, second succeeds; result counts one failed and one written.
- `test_fill_rechecks_current_lyrics`: file becomes synced between scan and fill; fill skips it.

Add HTTP tests for admin 401/403, report shape, 100-file cap, disabled-provider 400, and no writes on GET.

- [ ] **Step 2: Run tests and verify RED**

Run: `docker exec downtify-feature-py uv run pytest tests/test_lyrics_health.py tests/test_api_lyrics_health.py -q`
Expected: missing module/router failures.

- [ ] **Step 3: Implement scanner and API**

Use `library_catalog._scan_library_path_pairs(ctx)` for fresh disk truth and `read_audio_metadata` for provider metadata. Use `track_index.spotify_id_for_filename(stored)` when available so the lookup cache keys stay stable.

`scan_lyrics_health` reads `read_track_lyrics`; timed text that passes `looks_like_lrc` is `synced`, embedded plain is `plain_only`, otherwise `missing`. It never fetches or writes.

`fill_lyrics` normalizes/deduplicates requested paths, resolves each through `resolve_library_file`, re-reads current lyrics, skips files that already satisfy the active mode, forgets the song's cache entry, calls `lyrics.fetch(..., synced_only=settings['lyrics_synced_only'])`, writes through `write_to_file`, then re-reads to confirm. It sleeps 250 ms between attempted tracks. Errors use stable codes only.

Create the router with a context helper matching `library_health_api`. Reject more than 100 files with 400 and disabled/empty providers with 400 `lyrics_disabled`. Include it in `main.py`; add an admin auth rule before broader routes.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `docker exec downtify-feature-py uv run pytest tests/test_lyrics_health.py tests/test_api_lyrics_health.py tests/test_lyrics_providers.py -q`
Expected: all pass.

- [ ] **Step 5: Lint and commit**

```bash
git add downtify/lyrics_health.py downtify/lyrics_health_api.py main.py downtify/auth.py tests/test_lyrics_health.py tests/test_api_lyrics_health.py
git commit -m "feat(lyrics): add health scan and bounded fill API"
```

---

### Task 3: Lyrics health page and device offset controls

**Files:**
- Create: `frontend/src/model/lyricsHealth.js`
- Create: `frontend/src/lib/lyricsHealth.js`
- Create: `frontend/src/views/LyricsHealthView.vue`
- Create: `frontend/src/__tests__/lyricsHealth.test.js`
- Create: `frontend/src/__tests__/lyricsOffset.test.js`
- Test: `tests/test_users.py`
- Test: `frontend/src/__tests__/auth.test.js`
- Modify: `frontend/src/model/api.js`
- Modify: `downtify/users.py`
- Modify: `frontend/src/model/account.js`
- Modify: `frontend/src/model/playerPrefs.js`
- Modify: `frontend/src/components/player/LyricsPanel.vue`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/views/LibraryView.vue`
- Modify: `frontend/src/components/shell/SideNav.vue`
- Modify: `frontend/src/components/shell/BottomNav.vue`
- Modify: all eight `frontend/src/i18n/locales/*.js`

**Interfaces:**
- Produces: `scanLyricsHealth()`, `fillLyricsHealth(files)`.
- Produces pure helpers `lyricsStatusCounts(report)`, `eligibleLyricsFiles(report)`, `chunkFiles(files, size=100)`.
- Produces pure helpers `clampLyricsOffset(value)`, `formatLyricsOffset(value)`, `lyricsHighlightTime(audioTime, offset)`, `lyricsSeekTime(lineTime, offset)`.
- `usePlayerPrefs()` additionally returns `lyricsOffset` and a stable `lyricsDeviceId`; `model/account.js` loads/saves the current device's value through `lyrics_offsets` user preferences.
- Route: `/library/lyrics`, name `LyricsHealth`.

- [ ] **Step 1: Write failing frontend tests**

Add helper tests for zero-default status counts, eligibility, 100-file chunking, ±0.5 clamping, signed formatting, highlight time and inverse seek time.

Add model tests proving Axios envelopes are unwrapped and fill posts `{files}`.

Add an SSR test proving `LyricsHealthView` uses `PageHeader`, renders the admin-only state without scanning, and renders the loading state for an admin before the first scan.

Add a backend preference test proving `lyrics_offsets` keeps only bounded device keys/values and round-trips through user preferences. Add a frontend account test proving the current device reads its own offset and saving one device does not overwrite another.

Add a `LyricsPanel` timing test proving highlighting uses `audioTime + 0.25 + offset` and clicking a line seeks `line.time - offset`.

- [ ] **Step 2: Run tests and verify RED**

Run: `docker exec downtify-feature-py uv run pytest tests/test_users.py -q && docker exec downtify-feature-node npm --prefix frontend test -- --maxWorkers=1 src/__tests__/lyricsHealth.test.js src/__tests__/lyricsOffset.test.js src/__tests__/auth.test.js`
Expected: missing helper/model/view failures.

- [ ] **Step 3: Implement the page and offset**

Record the surface brief before editing UI: an Operate-page ledger with summary strip, status filter, findings table and explicit fill action; inherit the existing v4 world.

Implement the API/model/helpers and a responsive semantic table like Library Health. Scan is automatic for admins; **Find & save** sends eligible files in 100-file batches, shows batch progress, and refreshes the report at the end. Empty, error, partial-provider and per-file failure states are visible.

Add a Lyrics button to the Library header and keep the Library nav active on `/library/lyrics`.

Add `lyricsOffset` (default `0`) and a stable UUID `lyricsDeviceId` to browser-local player preferences. Extend `clean_preferences` with a bounded `lyrics_offsets` map (device key ≤64 chars, value clamped to ±0.5, at most 32 devices), and teach `model/account.js` to merge/save only the current device's entry. In `LyricsPanel`, show −0.1/+0.1 controls, a reset control, and the signed current value; clamp to ±0.5. Use the pure timing helpers for highlighting and line-click seek. The value is device-specific, backed up with the user, and never written to audio/LRC files.

Add all page/settings/offset keys to the eight locales.

- [ ] **Step 4: Run tests/build and verify GREEN**

Run: `docker exec downtify-feature-py uv run pytest tests/test_users.py -q && docker exec downtify-feature-node npm --prefix frontend test -- --maxWorkers=1 src/__tests__/lyricsHealth.test.js src/__tests__/lyricsOffset.test.js src/__tests__/auth.test.js src/__tests__/lrc.test.js src/__tests__/pageHeader.test.js src/__tests__/i18nParity.test.js && docker exec downtify-feature-node npm --prefix frontend run build`
Expected: all pass.

- [ ] **Step 5: Inspect and commit**

Run Prettier on changed frontend files, preserving pre-existing formatting in legacy files when that avoids unrelated churn. Run the Impeccable detector once on the finished UI. Verify desktop, ~780px and 390px layouts with a synthetic admin harness; record any unverified state.

```bash
git add downtify/users.py frontend/src/model/account.js frontend/src/model/lyricsHealth.js frontend/src/lib/lyricsHealth.js frontend/src/views/LyricsHealthView.vue frontend/src/__tests__/lyricsHealth.test.js frontend/src/__tests__/lyricsOffset.test.js frontend/src/__tests__/auth.test.js frontend/src/model/api.js frontend/src/model/playerPrefs.js frontend/src/components/player/LyricsPanel.vue frontend/src/router/index.js frontend/src/views/LibraryView.vue frontend/src/components/shell/SideNav.vue frontend/src/components/shell/BottomNav.vue frontend/src/i18n/locales tests/test_users.py .impeccable/surfaces
git commit -m "feat(lyrics): add health page and device offset controls"
```

---

### Task 4: Documentation, gates and wave close

**Files:**
- Create: `docs/features/lyrics-health.md`
- Modify: `docs/features/lyrics.md`
- Modify: `docs/features/index.md`
- Modify: `docs/api-reference.md`
- Modify: `README.md`
- Modify: `docs/superpowers/plans/2026-11-24-personal-server-program-roadmap.md`
- Modify: `.superpowers/sdd/2026-11-25-lyrics-health-offset/progress.md`

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces: user/API documentation and a review-ready wave.

- [ ] **Step 1: Document behavior and limits**

Document LRCLIB `/get`→`/search` fallback, synced-only mode, the three health statuses, explicit bounded fill behavior, format preservation, device-local offset semantics, and the Kugou evaluation/defer decision. Add endpoints to the API reference and the feature to README/docs index.

- [ ] **Step 2: Run full gates**

```bash
docker exec downtify-feature-py uv run pytest -q
docker exec downtify-feature-py uv run ruff check .
docker exec downtify-feature-py uv run ruff format --check .
docker exec downtify-feature-node npm --prefix frontend test -- --maxWorkers=1
docker exec downtify-feature-node npm --prefix frontend run build
docker exec downtify-feature-node npm --prefix docs test
docker exec downtify-feature-node npm --prefix docs run build
git diff --check
```

- [ ] **Step 3: Record completion and commit**

Update the ledger with real counts, review findings and deferred decisions. Mark the phase complete in the roadmap only after every gate is green.

```bash
git add docs README.md docs/superpowers/plans/2026-11-24-personal-server-program-roadmap.md
git commit -m "docs(lyrics): complete health and offset phase"
```

- [ ] **Step 4: Independent review, merge and deploy**

Create a review package from `1387368..HEAD`. Dispatch a read-only reviewer using a verified zero-cost active `opencode-go` model. Fix Critical/Important findings test-first, rerun gates, fast-forward merge into `feat/collections`, deploy, and verify live HEAD, health, container health, admin-only new endpoints and absence of error logs.

## Self-Review

- **Spec coverage:** LRCLIB fallback, synced-only mode, bulk scan/fill, ±0.5 device offset and preserved format writes all have owning tasks.
- **Kugou:** evaluated and explicitly deferred with reason; no hidden provider or default-on source is added.
- **Type consistency:** report/result keys and helper names are reused unchanged across backend, UI and tests.
- **Review Focus:** every line has a test in Task 1, 2 or 3.
- **Proportion:** the plan fixes interfaces, bounds and safety rules while leaving routine Vue/SQL bodies to the implementer.
