# Last.fm-style Listening Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Stats with the approved Last.fm-style canonical listening profile, without hourly/pattern visualizations or fabricated telemetry.

**Architecture:** Extend the existing canonical listening store with additive all-time profile aggregates and structured track rows. Rewrite only the Stats view around those fields, preserving existing API consumers and selected-period data.

**Tech Stack:** Python/FastAPI/SQLite, Vue 3, Vitest, pytest, Ruff.

**Spec:** `docs/superpowers/specs/2026-11-27-stats-listening-profile-design.md`

## Global Constraints

- Keep `/api/stats` backward compatible; additions only.
- Count canonical `listening_events` only; never sum raw provider observations.
- All-time profile is account-scoped; selected period remains 7/30/90 UTC days.
- No hour-of-day, weekday, heatmap, clock or 24-hour matrix in the Stats view.
- No fabricated seconds, completions, skips, versions, system IDs, storage, cache, codec or hardware.
- Preserve eight locales, Technical Gazette tokens, 0px radius, 2px rules and reduced motion.
- No new dependencies, provider calls or tables.

## Review Focus

- Old API consumers still receive `summary`, `top_tracks`, `recent`, `period`, `patterns`, `heatmap`, `day` and `pattern_detail` with unchanged semantics.
- Empty history and missing artist/album/title values render safe localized empty states rather than `undefined` or invented labels.
- Account scoping cannot leak another user's profile counts or rows.
- Four-week buckets use UTC boundaries, always contain four rows and sum canonical plays without double counting.
- Long track/artist/album names and mobile widths do not create page-level horizontal overflow.

---

### Task 1: Canonical all-time profile API

**Files:**
- Modify: `downtify/listening_history.py`
- Modify: `downtify/stats.py`
- Modify: `downtify/collections_api.py`
- Test: `tests/test_listening_history.py`
- Test: `tests/test_api_stats.py`

**Interfaces:**
- Produces: `playback.profile` with `first_at`, `last_at`, `unique`, `by_source`, `top_artists`, `top_albums`, `weeks`.
- Produces: structured `artist`, `title`, `album` on `playback.top_tracks` and `playback.recent`, preserving existing keys.

- [ ] **Step 1: Write failing store tests**

Add `test_all_time_profile_aggregates_are_canonical_and_user_scoped`: create two plays for user 1 (one Spotify, one Last.fm), one for user 2, with known artist/title/album values; assert `total`, `profile.unique`, `profile.by_source`, `first_at`, `last_at`, `top_artists`, `top_albums`, and structured `top_tracks`/`recent`.

Add `test_profile_weeks_are_four_consecutive_utc_buckets`: create plays at known offsets 0, 6, 7, 13, 14, 20, 21 and 27 days; assert four `{start,end,count}` rows, oldest first, each spanning seven days and summing the selected user's plays.

- [ ] **Step 2: Run store tests and verify RED**

Run: `.venv/bin/pytest tests/test_listening_history.py -q`
Expected: FAIL on missing `profile` or structured keys.

- [ ] **Step 3: Implement store aggregates**

In `ListeningStore.stats()`, add all-time unique/source/range queries, top artist/album queries, structured fields on top/recent rows, and four UTC week buckets derived from canonical rows.

- [ ] **Step 4: Run store tests and verify GREEN**

Run: `.venv/bin/pytest tests/test_listening_history.py -q`
Expected: PASS.

- [ ] **Step 5: Write failing API/fallback tests**

Add an API assertion for `playback.profile` and structured recent/top rows. Add an empty-store assertion that `profile` has empty range, zero unique/source counts and four zero week buckets. Add an activity-only `build_stats` test proving the fallback profile is derived from existing playback activity.

- [ ] **Step 6: Run API tests and verify RED**

Run: `.venv/bin/pytest tests/test_api_stats.py -q`
Expected: FAIL on missing `playback.profile`.

- [ ] **Step 7: Implement response/fallback parity**

Forward profile fields in `build_stats()`, derive an activity-only profile when `listening_stats` is absent, and add the same empty defaults in `collections_api.py`.

- [ ] **Step 8: Run API tests and verify GREEN**

Run: `.venv/bin/pytest tests/test_api_stats.py -q`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add downtify/listening_history.py downtify/stats.py downtify/collections_api.py tests/test_listening_history.py tests/test_api_stats.py
git commit -m "feat(stats): add canonical listening profile aggregates"
```

### Task 2: Profile view and locale contract

**Files:**
- Create: `frontend/src/lib/statsProfile.js`
- Modify: `frontend/src/views/StatsView.vue`
- Modify: `frontend/src/i18n/locales/{en,tr,es,pt-BR,el,fr,hu,bg}.js`
- Test: `frontend/src/__tests__/statsProfile.test.js`
- Test: `frontend/src/__tests__/pageHeader.test.js`
- Test: `frontend/src/__tests__/listeningSources.test.js`
- Test: `frontend/src/__tests__/statsLocale.test.js`
- Test: `frontend/src/__tests__/statsViewClientRender.test.js`

**Interfaces:**
- Consumes: `playback.profile`, structured `playback.top_tracks` and `playback.recent`, existing selected-period fields.
- Produces: `trackParts(row)` and `weekLabel(start,end,locale)` from `frontend/src/lib/statsProfile.js`.

- [ ] **Step 1: Write failing helper tests**

Add `statsProfile.test.js` covering structured row preference, `Artist - Title` fallback, title-only/artist-only fallback, blank rows, and localized week labels.

- [ ] **Step 2: Run helper test and verify RED**

Run: `npm test -- --run src/__tests__/statsProfile.test.js`
Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement display helpers**

Create `statsProfile.js` with only the two tested pure helpers.

- [ ] **Step 4: Run helper test and verify GREEN**

Run: `npm test -- --run src/__tests__/statsProfile.test.js`
Expected: PASS.

- [ ] **Step 5: Write failing Stats view tests**

Update the Stats fixture with `profile`, structured top/recent rows and a signed-in username. Assert profile masthead, four lifetime metrics, all-time source ledger, recent table, top artists/albums/tracks, four-week report, selected-period summary and absence of `stats.patterns`, `stats.activityHeatmap`, `stats.downloadsPerDay` and `stats.spotifyRecent`. Add an empty-profile render test.

- [ ] **Step 6: Run view tests and verify RED**

Run: `npm test -- --run src/__tests__/pageHeader.test.js src/__tests__/listeningSources.test.js`
Expected: FAIL on missing profile sections or forbidden legacy panels.

- [ ] **Step 7: Implement the profile view**

Rewrite `StatsView.vue` to the approved hierarchy. Keep loading/error states, `UiSegmented`, `UiEmpty`, `UiSkeleton`, count-up and existing locale/date formatting conventions. Remove pattern/day/heatmap/download/Spotify-only sections and their unused imports/state from this view.

- [ ] **Step 8: Add locale keys test-first**

Extend `statsLocale.test.js` with `profileSubtitle`, `archiveRange`, `topTrack`, `totalPlays`, `allTime`, `topArtists`, `topAlbums`, `listeningReport`, `canonicalPlays`, `periodSummary`, `archiveScope`, `sourcePriority`, `profileEmpty`, `hoursMinutes` and `weekLabel`.

- [ ] **Step 9: Run locale test and verify RED**

Run: `npm test -- --run src/__tests__/statsLocale.test.js`
Expected: FAIL on missing keys.

- [ ] **Step 10: Add all eight locale translations**

Add the new keys to every locale, preserving key parity and natural wording.

- [ ] **Step 11: Run Stats frontend tests and verify GREEN**

Run: `npm test -- --run src/__tests__/statsProfile.test.js src/__tests__/statsLocale.test.js src/__tests__/statsViewClientRender.test.js src/__tests__/pageHeader.test.js src/__tests__/listeningSources.test.js src/__tests__/statsPeriod.test.js`
Expected: PASS.

- [ ] **Step 12: Commit**

```bash
git add frontend/src/lib/statsProfile.js frontend/src/views/StatsView.vue frontend/src/i18n/locales frontend/src/__tests__
git commit -m "feat(ui): add Last.fm-style listening profile"
```

### Task 3: Documentation and verification

**Files:**
- Modify: `docs/features/stats.md`
- Modify: `docs/api-reference.md`
- Modify: `docs/superpowers/specs/2026-11-27-stats-listening-profile-design.md`

**Interfaces:**
- Consumes: completed Task 1 and Task 2 contracts.

- [ ] **Step 1: Update Stats documentation**

Describe the profile hierarchy, all-time vs selected-period semantics, four-week report, structured rows and removal of pattern/heatmap panels from the Stats view. Keep legacy API field documentation marked as retained for compatibility.

- [ ] **Step 2: Update API reference**

Document `playback.profile` and structured `top_tracks`/`recent` fields, including empty defaults and UTC week boundaries.

- [ ] **Step 3: Run formatting and static checks**

Run: `.venv/bin/ruff check downtify/listening_history.py downtify/stats.py downtify/collections_api.py tests/test_listening_history.py tests/test_api_stats.py`
Expected: PASS.

Run: `npm run format:check`
Expected: PASS for changed frontend files; format only those files if needed.

- [ ] **Step 4: Run full backend gates**

Run: `.venv/bin/pytest -q`
Expected: PASS with no failures.

- [ ] **Step 5: Run full frontend gates**

Run: `npm test`
Expected: PASS.

Run: `npm run build`
Expected: PASS.

- [ ] **Step 6: Run docs build**

Run the repository's documented docs build command.
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add docs/features/stats.md docs/api-reference.md docs/superpowers/specs/2026-11-27-stats-listening-profile-design.md
git commit -m "docs(stats): document listening profile"
```
