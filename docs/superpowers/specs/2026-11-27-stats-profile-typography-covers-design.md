# Stats profile typography and album covers

- **Date:** 2026-11-27
- **Status:** Approved — frontend-only refinement
- **Scope:** `frontend/src/views/StatsView.vue`, its tests and any pure display helper needed for cover matching

## Intent

Reduce the Stats profile's oversized display type and replace empty album-initial placeholders with real library artwork while preserving the Technical Gazette identity and canonical listening data.

## Goals

- Align Stats display type with the existing 20–32px design scale.
- Show real album covers through the existing `CoverArt` component.
- Keep initials only as the missing/broken-art fallback.
- Preserve eight locales, light/dark tokens, square geometry, 2px rules, responsive behavior and reduced motion.

## Non-goals

- No new provider calls, schema, API fields or dependencies.
- No change to canonical counts, source precedence, period semantics or legacy API fields.
- No global typography/token changes or redesign of other views.

## Constraints

- `/api/library/albums` already returns `title`, `artist` and `cover_file`; the frontend library model normalizes that to `cover` URLs.
- Album identity is case-insensitive `artist + album`, matching the existing `albumKey` helper.
- Stats must remain usable if the album index is unavailable or a cover is missing.

## Approaches

1. **Frontend-only library-index join (chosen).** Load the existing album index on demand, match top albums by `albumKey`, and render `CoverArt`. Align only StatsView display sizes. Smallest complete change; no API or data-model work.
2. **Backend-enriched `top_albums`.** Add `cover_file` to the profile response by joining the library catalog. More self-contained payload but couples listening aggregates to library scanning and expands backend/test scope.
3. **External artwork lookup.** Fetch provider covers on demand. Rejected: adds provider/provenance behavior and can still miss library-specific art.

## Design

- Username: `34/42px` → `28/32px`.
- Lifetime metrics: `34px` → `28px`.
- Top-track title/count: `24/30px` → `20/24px`.
- Period total and known-time values: `36/30px` → `30/24px`.
- Existing 13px table/meta text and 11px labels remain unchanged.
- Top albums use `<CoverArt :src="cover" :name="row.album" :alt="row.album" class="aspect-square" />`; missing art keeps the initials fallback.
- The approved 30px period total uses the `text-3xl` utility (one step down from `text-4xl`); the other compact sizes use explicit `text-[NNpx]` classes.

## Implementation notes

- A computed map joins `useLibrary().albums` to the profile's top albums with case-insensitive `albumKey(artist, album)`; albums with no cover URL are omitted so the initials fallback wins.
- The album index is requested on mount only when `albumsComplete` is false, and a rejected background lookup is swallowed — artwork is decoration, not required for Stats to render.
- The `CoverArt` fallback is locally restyled on the Stats instance only with `[&_.eyebrow]:font-display [&_.eyebrow]:text-[24px] [&_.eyebrow]:font-bold [&_.eyebrow]:text-fg`, so missing or broken art keeps the original 24px bold display initials. `CoverArt` itself is unchanged.

## Acceptance

- Tests prove real covers are selected by artist+album, missing covers fall back, and oversized Stats display classes are gone.
- Desktop/mobile renders preserve layout without horizontal overflow.
- Targeted and full frontend/backend/docs gates pass; no API/schema/dependency diff.
