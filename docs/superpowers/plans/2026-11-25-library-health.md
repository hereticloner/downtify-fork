# Library Health Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an admin-only, read-only Library Health report that compares disk audio with TrackIndex, playlist records, Monitor history and Navidrome mappings, explains each finding and exports a redacted JSON report.

**Architecture:** One focused backend module performs a fresh disk scan and read-only store lookups, returning a stable report shape. A small FastAPI router exposes the report and its redacted export; a new Vue route renders category filters and a responsive findings table using the existing v4 components.

**Tech Stack:** Python 3.12+, FastAPI, SQLite, Mutagen, Vue 3, Vue Router, Axios, Vitest, Vite.

**Spec:** `docs/superpowers/specs/2026-11-24-personal-server-feature-program-design.md` §6.9, §6.14 and Faz 9.

## Global Constraints

- First version is read-only: no repair, delete, reconcile or write endpoint.
- Existing flat files, API responses and collection documents remain compatible.
- Preserve v4 identity: `#F3F3F0` / `#171717` / `#0047FF`, 0 radius, 2px rules, flat surfaces.
- Preserve `prefers-reduced-motion` behavior and the eight shipped locales.
- Port remains `8000`; no PostgreSQL, OIDC, new audio provider or upstream merge.
- No new dependency for scanning, export or UI.
- Export must omit filesystem paths, record IDs, Spotify IDs, URLs, tokens and personal data.
- Every deploy verifies HEAD, `/api/health`, container health and the new routes.

## Review Focus

- A missing file referenced by a playlist/watch is `missing_file`; an unreferenced missing TrackIndex row is `orphan_record`, not both.
- A moved file whose `content_key` still exists is `path_mismatch` with a suggested path, never `missing_file`.
- A Navidrome row whose `content_key` no longer exists is `stale_mapping` even when its filename is empty.
- Missing title/artist tags are `missing_metadata` even when the filename supplies a display fallback.
- A scan and its export leave audio, SQLite rows and settings unchanged; the export contains no path, ID, URL or secret.
- Auth keeps both report and export admin-only; normal clients receive 403.

---

### Task 1: Read-only scanner and redaction

**Files:**
- Create: `downtify/library_health.py`
- Create: `tests/test_library_health.py`
- Modify: `downtify/navidrome_index.py`
- Modify: `tests/test_navidrome_index.py`

**Interfaces:**
- Consumes: `LibraryContext`, `TrackIndex.all_rows()`, `PlaylistCatalog.all_track_rows()`, `PlaylistMonitorDB.list_all_downloaded_tracks()`, `NavidromeIndex.all_rows()`, `read_audio_metadata()`, `file_content_key()`.
- Produces: `scan_library_health(ctx, *, track_index=None, playlist_catalog=None, monitor_db=None, navidrome_index=None) -> dict[str, Any]` and `redact_health_report(report: dict[str, Any]) -> dict[str, Any]`.
- Report shape: `{version: 1, scanned_at: ISO8601, summary: {disk_files, indexed_tracks, findings, by_category}, sources: {disk, track_index, playlist_catalog, monitor, navidrome}, findings: [{id, category, severity, source, file, record_id, recommendation, suggested_path?}], warnings: [str]}`.
- Categories, always present in `by_category`: `missing_file`, `path_mismatch`, `stale_mapping`, `missing_metadata`, `orphan_record`.
- Recommendation codes: `redownload`, `reconcile_paths`, `refresh_navidrome`, `repair_metadata`, `review_record`.

- [ ] **Step 1: Write failing scanner tests**

Add these tests to `tests/test_library_health.py`:

- `test_missing_referenced_track_is_missing_file`: a TrackIndex row points to a absent file and the same Spotify ID appears in a playlist row; exactly one `missing_file` finding has `recommendation == 'redownload'`.
- `test_unreferenced_missing_track_is_orphan_record`: the same absent TrackIndex row without playlist/watch references yields one `orphan_record` with `recommendation == 'review_record'`.
- `test_moved_file_is_path_mismatch`: register a real file, move it without changing basename/size, scan; one `path_mismatch` has `suggested_path == 'Moved/Track.mp3'` and no `missing_file` exists for that record.
- `test_playlist_and_monitor_missing_files_are_reported`: absent catalog and monitor filenames each produce `missing_file` with their own `source`.
- `test_navidrome_missing_content_key_is_stale_mapping`: store a Navidrome mapping, remove the file, scan; one `stale_mapping` has `recommendation == 'refresh_navidrome'`.
- `test_missing_title_or_artist_is_missing_metadata`: monkeypatch `read_audio_metadata` to return empty `title`/`artist` for one disk file; it is reported even though its filename is `Artist - Title.mp3`.
- `test_scan_is_read_only`: seed stores and one audio file, capture file bytes plus SQLite table rows, scan twice, and assert bytes/rows are unchanged.
- `test_redacted_export_contains_no_identifiers`: seed findings containing `/home/yeet/secret/Token.mp3`, a Spotify ID and `https://private.example/token`; `redact_health_report` preserves category/source/recommendation/counts but none of those strings or the keys `file`, `record_id`, `suggested_path`.

Add `test_all_rows_returns_navidrome_mappings` to `tests/test_navidrome_index.py`: after `store`, `all_rows()` returns one dict with `content_key`, `filename`, `navidrome_song_id`, `spotify_track_id`, `resolved_at`.

- [ ] **Step 2: Run the tests and verify RED**

Run: `docker exec downtify-feature-py uv run pytest tests/test_library_health.py tests/test_navidrome_index.py -q`
Expected: import/attribute failures for the new module and `all_rows`.

- [ ] **Step 3: Implement the scanner**

In `downtify/navidrome_index.py`, add `all_rows() -> list[dict[str, Any]]` using the existing read connection and return all five columns.

In `downtify/library_health.py`:

- Use `library_catalog._scan_library_path_pairs(ctx)` for a fresh, non-caching disk snapshot; build `disk_by_path` and `disk_by_content_key`.
- Read raw tags once per disk file with `read_audio_metadata`; emit `missing_metadata` when title or artist is empty.
- Build the set of Spotify IDs referenced by playlist and monitor rows before classifying TrackIndex rows.
- For each index/catalog/monitor row: existing path → no finding; matching content key → `path_mismatch`; otherwise referenced rows → `missing_file`, unreferenced TrackIndex rows → `orphan_record`.
- For each Navidrome row: content key absent from disk → `stale_mapping`.
- Sort findings by category order, source, file and record ID; include every category in `by_category`.
- Catch store read failures per source and append a stable warning code such as `track_index_unavailable`; never include exception text or paths in warnings.
- Implement `redact_health_report` by rebuilding the document with only `version`, `scanned_at`, `summary`, `sources`, `warnings`, and findings reduced to sequential `id`, `category`, `severity`, `source`, `recommendation`.

- [ ] **Step 4: Run the tests and verify GREEN**

Run: `docker exec downtify-feature-py uv run pytest tests/test_library_health.py tests/test_navidrome_index.py -q`
Expected: all pass.

- [ ] **Step 5: Lint and commit**

Run: `docker exec downtify-feature-py uv run ruff check downtify/library_health.py downtify/navidrome_index.py tests/test_library_health.py tests/test_navidrome_index.py && docker exec downtify-feature-py uv run ruff format --check downtify/library_health.py downtify/navidrome_index.py tests/test_library_health.py tests/test_navidrome_index.py`

```bash
git add downtify/library_health.py downtify/navidrome_index.py tests/test_library_health.py tests/test_navidrome_index.py
git commit -m "feat(library-health): add read-only diagnostic scanner"
```

---

### Task 2: Admin API and redacted export

**Files:**
- Create: `downtify/library_health_api.py`
- Create: `tests/test_api_library_health.py`
- Modify: `main.py`
- Modify: `downtify/auth.py`

**Interfaces:**
- Consumes: Task 1 scanner/redactor and `api.state` stores.
- Produces: `GET /api/library/health` and `GET /api/library/health/export`, both admin-only.

- [ ] **Step 1: Write failing HTTP tests**

Add `tests/test_api_library_health.py`:

- `test_health_report_returns_scanner_shape`: seed `api.state` with real stores and a temp downloads directory; GET returns 200 and the Task 1 report keys.
- `test_health_export_is_redacted_json`: seed a finding path/ID through the scanner; GET export returns 200, `content-type: application/json`, a `Content-Disposition` attachment header, and JSON containing no path/ID.
- `test_health_routes_are_admin_only`: assert `classify('GET', '/api/library/health') == ADMIN` and the same for `/export`; a signed-in non-admin client receives 403.
- `test_health_routes_do_not_write`: capture store rows and audio bytes around both GETs and assert they are unchanged.

- [ ] **Step 2: Run the tests and verify RED**

Run: `docker exec downtify-feature-py uv run pytest tests/test_api_library_health.py -q`
Expected: 404/405 before the router and auth rules exist.

- [ ] **Step 3: Implement the router and auth**

Create `downtify/library_health_api.py` with a private `_context()` matching `collections_api._library_context()`. Add sync GET endpoints so FastAPI runs the blocking scan in its worker pool. The export endpoint serializes `redact_health_report(report)` with `ensure_ascii=False`, `indent=2` and filename `downtify-library-health.json`.

Include the router in `main.py` beside `collections_api`. Add `(_ALL, r'^/api/library/health(/|$)', ADMIN)` before broader library rules in `downtify/auth.py`.

- [ ] **Step 4: Run the tests and verify GREEN**

Run: `docker exec downtify-feature-py uv run pytest tests/test_api_library_health.py tests/test_library_health.py -q`
Expected: all pass.

- [ ] **Step 5: Lint and commit**

Run: `docker exec downtify-feature-py uv run ruff check downtify/library_health_api.py main.py downtify/auth.py tests/test_api_library_health.py && docker exec downtify-feature-py uv run ruff format --check downtify/library_health_api.py main.py downtify/auth.py tests/test_api_library_health.py`

```bash
git add downtify/library_health_api.py main.py downtify/auth.py tests/test_api_library_health.py
git commit -m "feat(library-health): expose admin report and redacted export"
```

---

### Task 3: Health page, route and eight locales

**Files:**
- Create: `frontend/src/model/libraryHealth.js`
- Create: `frontend/src/lib/libraryHealth.js`
- Create: `frontend/src/views/LibraryHealthView.vue`
- Create: `frontend/src/__tests__/libraryHealth.test.js`
- Modify: `frontend/src/model/api.js`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/views/LibraryView.vue`
- Modify: all eight `frontend/src/i18n/locales/*.js`

**Interfaces:**
- Consumes: Task 2 endpoints.
- Produces: `scanLibraryHealth()`, `exportLibraryHealth()`; pure `categoryCounts(report)` and `filterFindings(findings, category)` helpers.
- Route: `/library/health`, name `LibraryHealth`.

- [ ] **Step 1: Write failing frontend tests**

Add `frontend/src/__tests__/libraryHealth.test.js`:

- `categoryCounts` returns all five categories with zero defaults and adds finding counts.
- `filterFindings` returns every finding for `all`, only matching rows for a category, and tolerates missing arrays.
- `scanLibraryHealth` unwraps `res.data`; `exportLibraryHealth` calls the API with `{responseType: 'blob'}` and returns the Blob.
- A small SSR render test proves `LibraryHealthView` uses `PageHeader` for its `h1` and renders the admin-only state without calling the API.

- [ ] **Step 2: Run the tests and verify RED**

Run: `docker exec downtify-feature-node npm --prefix frontend test -- --maxWorkers=1 src/__tests__/libraryHealth.test.js`
Expected: missing module/view failures.

- [ ] **Step 3: Implement the page**

Record the surface brief under `.impeccable/surfaces/library-health.md` before editing UI. Direction: an Operate-page diagnostic ledger; first viewport is a summary strip followed by category filters and findings; no new visual tokens.

Implement:

- `api.getLibraryHealth()` and `api.exportLibraryHealth()`; export uses Axios `responseType: 'blob'`.
- `model/libraryHealth.js` wrappers and `lib/libraryHealth.js` pure helpers.
- `LibraryHealthView.vue` with `PageHeader`, explicit scan/export buttons, loading/error/empty states, one summary block per category, category filter, and a semantic table.
- The table wrapper has `role="region"`, `tabindex="0"`, an accessible name, sticky headers, and a container-query stacked layout below 600px with visible per-cell labels. No rounded progress widget is needed.
- Show live admin paths in a mono column; show translated recommendation text. State clearly that the page never repairs anything.
- Non-admin users see the existing `UiEmpty` + lock pattern.
- Add the lazy route and an admin-only Health button in `LibraryView`'s header.
- Add `libraryHealth.*` keys to all eight locales: title, subtitle, scan, export, scannedAt, healthy, healthyHint, adminOnly, adminOnlyHint, loadFailed, noMatches, clearFilter, categories and recommendations for all five categories, source labels, and export filename text.

- [ ] **Step 4: Run frontend tests/build and verify GREEN**

Run: `docker exec downtify-feature-node npm --prefix frontend test -- --maxWorkers=1 src/__tests__/libraryHealth.test.js src/__tests__/pageHeader.test.js && docker exec downtify-feature-node npm --prefix frontend run build`
Expected: tests and production build pass.

- [ ] **Step 5: Inspect and commit**

Run Prettier on changed frontend files and the Impeccable detector once:

`docker exec downtify-feature-node npx prettier --check src/model/libraryHealth.js src/lib/libraryHealth.js src/views/LibraryHealthView.vue src/views/LibraryView.vue src/model/api.js src/router/index.js src/__tests__/libraryHealth.test.js src/i18n/locales/*.js`

`/tmp/impeccable-engine detect --json --changed`

Capture desktop and ~780px renders if an authenticated local harness is available; otherwise record visual verification as open. Fix mechanical findings before commit.

```bash
git add frontend/src/model/libraryHealth.js frontend/src/lib/libraryHealth.js frontend/src/views/LibraryHealthView.vue frontend/src/__tests__/libraryHealth.test.js frontend/src/model/api.js frontend/src/router/index.js frontend/src/views/LibraryView.vue frontend/src/i18n/locales .impeccable/surfaces/library-health.md
git commit -m "feat(library-health): add diagnostic page and locales"
```

---

### Task 4: Documentation, gates and wave close

**Files:**
- Create: `docs/features/library-health.md`
- Modify: `docs/features/index.md`
- Modify: `docs/api-reference.md`
- Modify: `README.md`
- Modify: `docs/superpowers/plans/2026-11-24-personal-server-program-roadmap.md`
- Modify: `.superpowers/sdd/2026-11-25-library-health/progress.md`

**Interfaces:**
- Consumes: completed Tasks 1–3.
- Produces: user/API documentation and a review-ready wave.

- [ ] **Step 1: Document behavior and limits**

Document the five categories, recommendation-only behavior, admin scope, fresh disk scan, redacted export fields, and the fact that no file/database/settings repair occurs. Add the feature to the docs index, API endpoint table and README feature list.

- [ ] **Step 2: Run full gates**

Run all of these and fix failures test-first:

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

Update the SDD ledger with actual test counts, review findings and any deferred visual verification. Mark Library Health complete in the roadmap only after every gate is green.

```bash
git add docs README.md docs/superpowers/plans/2026-11-24-personal-server-program-roadmap.md
git commit -m "docs(library-health): complete phase and verification"
```

- [ ] **Step 4: Independent review, merge and deploy**

Create a review package from `d3e1fef..HEAD`. Dispatch a read-only reviewer using a verified zero-cost active `opencode-go` chat model. Fix all Critical/Important findings test-first, rerun gates, fast-forward merge into `feat/collections`, deploy with `ssh home '~/bin/downtify-deploy.sh'`, and verify:

- live HEAD equals merged HEAD;
- `/api/health` returns `{"status":"ok","version":"4.0.0"}`;
- container health is `healthy`;
- `/api/library/health` and `/api/library/health/export` require admin and return the expected shape when authorized.

## Self-Review

- **Spec coverage:** §6.9's disk/index/playlist/Monitor/Navidrome comparison, five categories, safe recommendations, no automatic repair and redacted export are all owned by Tasks 1–4.
- **Type consistency:** `scan_library_health` and `redact_health_report` names and report keys are reused unchanged by API, UI helpers and tests.
- **Review Focus:** each line has an explicit test in Task 1 or Task 2.
- **Proportion:** the plan specifies interfaces, classifications and gates; it leaves routine Vue/SQL bodies to the implementer.
