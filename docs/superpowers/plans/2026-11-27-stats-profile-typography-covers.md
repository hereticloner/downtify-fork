# Stats Profile Typography and Covers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Stats less visually loud and show real library album artwork without changing its API or visual identity.

**Architecture:** Reuse the existing library album index and `CoverArt` component inside StatsView. Match albums with the existing case-insensitive `albumKey(artist, album)` helper; keep initials as fallback. Reduce only StatsView display-size utilities to the approved role scale.

**Tech Stack:** Vue 3, Vitest, existing library model, Tailwind utilities

**Spec:** `docs/superpowers/specs/2026-11-27-stats-profile-typography-covers-design.md`

## Global Constraints

- No new provider calls, schema, API fields or dependencies.
- No change to canonical counts, source precedence, period semantics or legacy API fields.
- Preserve eight locales, light/dark tokens, square geometry, 2px rules, responsive behavior and reduced motion.
- No global typography/token changes or redesign of other views.

## Review Focus

- No matching library album: keep the initials fallback and all counts visible.
- Album-index request failure: Stats still renders; the background cover lookup must not reject unhandled.
- Same album title from different artists: match by artist + album, never title alone.
- Case differences between Stats and library metadata: reuse case-insensitive `albumKey`.
- Long localized names and narrow/mobile layouts: covers stay square, text truncates, page does not overflow.

---

### Task 1: Compact type and real album covers

**Files:**
- Modify: `frontend/src/views/StatsView.vue`
- Modify: `frontend/src/__tests__/pageHeader.test.js`
- Modify: `docs/superpowers/specs/2026-11-27-stats-profile-typography-covers-design.md`

**Interfaces:**
- Consumes: `useLibrary().albums`, `useLibrary().albumsComplete`, `useLibrary().ensureAlbums()`, `albumKey(artist, album)`, `CoverArt`.
- Produces: Stats top-album rows with a display-only `cover` URL; no API contract change.

- [ ] **Step 1: Make the library mock cover-aware and write failing render tests**

Refactor the existing `/src/model/library` mock to expose mutable `albums`, `albumsComplete` and `ensureAlbums`. Add tests asserting: matching artist+album renders `/cover?file=...` with album alt text; a missing match renders initials; same-title/different-artist rows select their own covers; case-only differences match; long names keep `truncate`; the background `ensureAlbums()` call has a rejection guard.

Run: `npm test -- --run src/__tests__/pageHeader.test.js`
Expected: FAIL because StatsView still renders initials for every album.

- [ ] **Step 2: Implement cover lookup and rendering**

Import `CoverArt`, `useLibrary` and `albumKey`. Build a computed `artist+album → cover` map from `library.albums.value`, map `profile.top_albums` to rows with `cover`, and replace the initials-only square with `CoverArt`. On mount, call `ensureAlbums()` only when `albumsComplete` is false, swallowing background lookup failure so Stats remains usable.

Run: `npm test -- --run src/__tests__/pageHeader.test.js`
Expected: PASS.

- [ ] **Step 3: Write the failing typography contract test**

Add a source/render assertion that StatsView uses `sm:text-[32px]`, `text-[28px]`, `text-[24px]` and `text-[20px]`, and no longer contains `sm:text-[42px]`, `text-[34px]`, `text-[36px]` or `text-[30px]` for the approved display roles.

Run: `npm test -- --run src/__tests__/pageHeader.test.js`
Expected: FAIL on the old oversized classes.

- [ ] **Step 4: Apply the compact display scale**

Username `34/42 → 28/32`; lifetime metrics `34 → 28`; top-track title/count `24/30 → 20/24`; period total `36 → 30`; known track time `30 → 24`. Keep 13px table/meta text and 11px labels unchanged.

Run: `npm test -- --run src/__tests__/pageHeader.test.js`
Expected: PASS.

- [ ] **Step 5: Verify the whole surface**

Run: `npm test -- --run src/__tests__/pageHeader.test.js src/__tests__/statsViewClientRender.test.js src/__tests__/motionBatch3.test.js`
Expected: PASS.

Run: `npm test && npm run build` in `frontend/`
Expected: PASS.

Run: `.venv/bin/pytest -q`
Expected: PASS.

Run: `.venv/bin/ruff check .`
Expected: PASS.

Run: `npm test && npm run build` in `docs/`
Expected: PASS.

Capture the Stats profile at 1440px and 390px with representative covers and long names; assert no horizontal page overflow and no console errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/StatsView.vue frontend/src/__tests__/pageHeader.test.js docs/superpowers/specs/2026-11-27-stats-profile-typography-covers-design.md
git commit -m "fix(ui): compact stats type and show album covers"
```
