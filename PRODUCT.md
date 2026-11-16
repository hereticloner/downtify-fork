# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary user is the owner, yeet — a single power user who self-hosts on a home server (CasaOS, Ubuntu) and uses the app daily: desktop for library and download work, phone (installed PWA) for listening away from the desk. Turkish-speaking; the interface ships eight languages and Turkish is the one he reads.

The product also supports household accounts (an admin creates accounts for other people, each with their own settings). Only the owner is a confirmed user — no other accounts, sessions or activity are evidenced. Do not invent a second persona.

## Product Purpose

Downtify is a self-hosted music downloader that also plays what it downloads. Paste a Spotify or YouTube Music link, or import a CSV from Soundiiz/TuneMyMusic/Exportify, and a correctly tagged audio file lands in the library — no Spotify account, no Premium, no API keys. Then the same tab plays that library, with synced lyrics, an editable queue and a keyboard-first transport.

Success means the library is complete, correctly tagged and one tab away from playing, and the unattended work — long playlist downloads, playlist/artist watches, restarts — runs without supervision.

## Positioning

Metadata comes from the public `open.spotify.com/embed` pages and the audio is matched on YouTube Music, all inside one Docker container. A neighbouring self-hosted downloader either needs Spotify credentials to read metadata or stops at the download, leaving playback to a separate media server. Downtify's claim is the closed loop: link → tagged file → play, with no account anywhere in the path.

## Operating Context

- Runs as a single Docker container on the owner's home server; reached over the LAN and the tailnet, and publicly at `down.akinyigit.com` through a Cloudflare Tunnel. Public exposure is deliberate (sharing), not an oversight.
- Maintained as a fork: `hereticloner/downtify-fork`, branch `feat/collections`, tracking upstream `henriquesebastiao/downtify` (currently 4.0.0). Upstream features arrive as prioritised batches, so the UI must survive being extended feature-by-feature rather than designed once.
- Deploys are `docker compose build` + `up -d` on the server; health check plus a live CSS/asset check confirm what shipped. Visual work is verified at real widths (2560px desktop, ~780px phone) before it is called done.
- The library lives as audio files on disk, with playlists as M3U and app state in the app's own store; sidecar consumers (Jellyfin, Navidrome, Plex) read the same files.
- Project documentation and design decisions live in this vault folder (`🏰 300-Projects/Downtify/`), including `redesign/` mockups and decision records.

## Capabilities and Constraints

Confirmed capabilities: Spotify/YouTube Music track, album, playlist and artist downloads plus free-text search and CSV import; MP3/FLAC/M4A/OGG/OPUS at chosen bitrate; pausable, restart-surviving queue; Deezer Charts and Finder, Discover from the existing library; synced lyrics (LRCLIB, NetEase); full-screen player with queue reorder, sleep timer, shortcuts, media keys, experimental EQ; Library/Album/Artist/Playlist/Queue views with filtering, multi-select, ZIP download; user playlists; Collections with smart rules; Playlist Monitor watches; Liked songs; Stats with a year heatmap; Telegram notifications; Last.fm scrobbling; Spotify Mirror and Spotify Sync (opt-in); Navidrome mirroring; music trash and download exclusions (opt-in); existing-folder import, library upgrade, replace audio; Stats/Storage/Trash/Monitor admin screens; users and activity log; light/dark themes and eight locales.

Constraints: the pipeline is `yt-dlp` + `ffmpeg` + `mutagen`, so format and tagging behaviour is bounded by those tools; audio on disk and the app's store are the truth; the test gates are the vitest suite and the pytest suite plus a production build — a change that breaks them is not shippable; nothing may delete a song outright outside the trash/exclusion paths.

Undecided or unfinished: the Android app; web UI for the API-only streaming and similar-tracks endpoints; Monitor/Collections/Trash right-hand columns that have no API field behind them; Similar match segments; the Charts top-three block.

## Brand Commitments

The product keeps the upstream name **Downtify** — the fork is not rebranded.

The visual world is locked by the owner's decision (2026-11-12, "technical gazette" hard brutalism): zero radius, 2px structural rules, no shadows, blur or glow, a single accent `#0047FF` reserved for state, light as default with a full dark inversion, full-colour covers. Typography was revised in the same decision toward comfort: Space Grotesk headings, Inter for body/table/form, Inter Tight for small uppercase labels, JetBrains Mono only for technical data (hash, bitrate, path, time). The binding record is `redesign/secim.md` with the executed tokens in `frontend/src/styles/tokens.css`; the identity comes from geometry and restraint, not from a showy typeface.

## Evidence on Hand

- Working code in the fork (branch `feat/collections`, v4.0.0 tokens in place), a large vitest suite and a pytest suite, and a live deployment that has been health-checked.
- 38 review mockups (24 desktop, 10 mobile) with an index in `redesign/mockups/`, plus the direction-selection and typography-revision records in `redesign/secim.md`.
- Vault project notes: catalog/collections handoff, TODO, upstream-port plan, UI-round bundle, improvement audit.
- Absences that future work must not fill in: there are no testimonials, no external users, no press, no marketing screenshots and no listening analytics beyond the in-app Stats page. Do not invent proof, ratings, user counts or brand partners.

## Product Principles

1. The library is the product: a correctly tagged file on disk outranks any clever view of it.
2. Self-hosted stays self-hosted: no required account, key or cloud service; every outbound integration is opt-in and can be turned back off.
3. Unattended must be trustworthy: long downloads, watches and restarts never lose state and never silently drop work.
4. Never destroy music: removal goes through the trash or an exclusion, and a wrong match is replaced rather than overwritten.
5. The UI is a workspace, not a showreel — density and keyboard reach over decoration, but readable type and listening comfort outrank the costume of an engineer's terminal.

## Accessibility & Inclusion

No formal standard has been agreed; record a target before claiming compliance. Known facts to preserve: eight shipped locales with Turkish among them, light and dark themes, keyboard-navigable track lists with shortcuts and media keys, and a phone layout that carries the same features rather than a reduced subset.
