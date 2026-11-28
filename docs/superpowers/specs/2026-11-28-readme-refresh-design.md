# GitHub README Refresh Design

**Status:** Approved 2026-11-28

**Scope:** `hereticloner/downtify-fork` GitHub landing page

## Intent

Make the fork's repository page useful on first visit: explain what it is, get a local instance running, and distinguish ordinary Spotify-link downloads from optional Spotify account integrations.

## Goals

- Lead with a short explanation and accurate screenshots.
- Provide a copy-paste Docker quick start with persistent-data and first-login guidance.
- Explain that pasting Spotify links needs no Spotify account, API key or Premium.
- Document optional Spotify Mirror/Sync requirements without implying they are required for downloads.
- State the current Stats source model: Downtify + Last.fm; Spotify-only history is archived but excluded from Stats.
- Keep detailed setup in `docs/features/` and link to it.
- Preserve upstream attribution, AGPL-3.0 licensing and the legal warning.

## Non-goals

- No production code, API, UI, dependency or deployment changes.
- No new documentation site or separate project homepage.
- No credentials, live URLs, personal server details or user data in the README.
- No claim that the fork publishes ready-made images or mirrors upstream releases.

## Constraints

- README-only content change plus process documents under `docs/superpowers/`.
- Existing untracked files in the working tree remain untouched.
- Keep the v4 visual identity and existing verified screenshot assets.
- Do not use the stale pre-Last.fm Stats screenshot; remove it unless replaced by a verified current capture.
- Stage only intended files and push `feat/collections` fast-forward.

## Approaches considered

1. **README-first refresh — chosen.** Rewrite the existing repository README into a concise landing page. Smallest complete change, works directly on GitHub, and keeps deep documentation in the existing VitePress pages.
2. **Separate homepage/docs-site redesign.** More visual freedom, but duplicates content and adds build/deployment scope the user did not request.
3. **Section reorder only.** Fast, but leaves the stale Stats claim, long feature paragraph and incomplete Spotify setup guidance intact.

## Content structure

1. Wordmark, one-sentence fork description, upstream/license badges and navigation.
2. Hero screenshot.
3. Feature table grouped by Downloading, Library, Listening, Automation, Safety and Interface.
4. Docker quick start, first login, persistent volumes and authentication warning.
5. Spotify connections:
   - Link downloads: anonymous metadata lookup; no account/API key/Premium.
   - Optional Mirror: Premium, own Spotify developer app, Web API, exact Redirect URI, PKCE client ID, connect and device selection.
   - Optional packaged Mirror device: `SOLOIST_API_KEY`, x86-64 image, one-time pairing, 90-day rebuild note; silent listening-history device.
   - Optional Sync: reuses Mirror OAuth and may require reconnect for playlist scopes.
6. Current Stats/Last.fm model.
7. Supported inputs, documentation links, credits, license and legal warning.

## Verification

- Every relative Markdown link resolves locally.
- Every referenced image exists and is suitable for the current README.
- Prettier check passes for the changed Markdown.
- `git diff --check` passes.
- Pushed commit and remote branch are verified; no deploy is performed.
