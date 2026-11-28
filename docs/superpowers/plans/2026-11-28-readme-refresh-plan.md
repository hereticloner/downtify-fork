# GitHub README Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Refresh the fork's GitHub README with a clear Docker setup and accurate optional Spotify integration guidance.

**Architecture:** Rewrite one Markdown landing page using existing screenshots and feature documentation. No application code or runtime behavior changes.

**Tech Stack:** Markdown, GitHub-flavored Markdown, Prettier

**Spec:** `docs/superpowers/specs/2026-11-28-readme-refresh-design.md`

## Global Constraints

- Modify only `README.md` and the approved design/plan documents.
- Preserve existing untracked files.
- Do not include credentials, private URLs, host paths or live user data.
- Do not change production code, dependencies, configuration or deployments.
- State that Spotify-link downloads need no Spotify account, while Mirror/Sync are optional Premium integrations.
- State that Stats counts Downtify + Last.fm only; Spotify-only history is archived but excluded.
- Stage explicit paths only and push `feat/collections` fast-forward.

## Review Focus

- A first-time reader must not think a Spotify account is required to download pasted links.
- Docker instructions must preserve `docker/downloads` and `docker/data`.
- Spotify Redirect URI guidance must say it must exactly match the browser-reachable callback URL.
- Mirror setup must not imply audible output; it is a silent listening-history device.
- The README must not display the stale pre-Last.fm Stats screenshot or claim Spotify-only plays appear in Stats.

---

### Task 1: Rewrite the GitHub landing page

**Files:**

- Modify: `README.md`
- Create: `docs/superpowers/specs/2026-11-28-readme-refresh-design.md`
- Create: `docs/superpowers/plans/2026-11-28-readme-refresh-plan.md`

**Interfaces:**

- Consumes: existing `assets/readme/*` screenshots and `docs/features/*.md` pages.
- Produces: a concise README with stable navigation anchors and links.

- [x] **Step 1: Replace the long feature paragraph with a grouped feature table linking to existing docs.**
- [x] **Step 2: Rewrite Quick start with clone, build, localhost, default login, password-change warning and persistent-volume notes.**
- [x] **Step 3: Add a Spotify connections section separating anonymous link downloads from optional Mirror/Sync setup.**
- [x] **Step 4: Update Stats copy to Last.fm + Downtify only and remove the stale Stats screenshot from the gallery.**
- [x] **Step 5: Preserve supported inputs, upstream documentation, attribution, license and legal warning.**

### Task 2: Verify and publish the documentation change

**Files:**

- Modify: `README.md`
- Test: local link/asset checks, Prettier, `git diff --check`

**Interfaces:**

- Consumes: Task 1 README.
- Produces: a verified fast-forward commit on `origin/feat/collections`.

- [x] **Step 1: Check every relative Markdown link and local image reference resolves.**
- [x] **Step 2: Run Prettier check on `README.md` and fix only formatting if needed.**
- [x] **Step 3: Run `git diff --check` and inspect the final diff for credentials, private URLs and stale claims.**
- [x] **Step 4: Stage only the three intended files and commit with `docs: refresh fork README and setup guide`.**
- [x] **Step 5: Push `feat/collections`, verify remote HEAD equals local HEAD, and report that no deploy occurred.**
