---
icon: lucide/mic-vocal
---

# Lyrics health

**Library → Lyrics** opens an admin-only, read-only report of the lyrics saved
with the files on disk. It checks the `.lrc` sidecar and the lyrics embedded in
the audio tags, then groups tracks into three statuses:

| Status | Meaning |
|---|---|
| **Synced** | A sidecar or embedded lyric contains LRC timestamps |
| **Plain only** | Lyrics exist, but they are not time-synced |
| **Missing** | No usable lyrics were found |

The page reads a fresh disk snapshot. If the downloads folder or a configured
external music folder cannot be read, the report is marked **partial** instead
of showing a healthy empty library.

## Find & save

**Find & save** is an explicit admin action. It sends only the eligible gaps to
the existing provider chain in batches of at most 100 files, waiting 250 ms
between tracks. In normal mode, already-plain lyrics are left alone; with
**Synced lyrics only** enabled, plain-only tracks are eligible too.

Before writing, Downtify checks the file again. Already-synced tracks are
skipped, provider misses are reported, and one failed track does not stop the
rest of the batch. Found lyrics use the same MP3/FLAC/M4A/Opus tag and `.lrc`
write path as downloads and library upgrades. The page never deletes audio.

## Synced-only mode

In **Settings → Tags & lyrics**, turn on **Synced lyrics only** to ignore
plain-only provider results and keep looking for timed lyrics. The setting
applies to new downloads, external-folder sync and library upgrades. It is off
by default, so existing behavior is unchanged.

## LRCLIB fallback

Downtify first asks LRCLIB's exact `/api/get` endpoint. On a miss it searches
`/api/search`, then accepts only a candidate whose title and artist line up,
using album and duration to choose between close matches. A wrong-artist or
wrong-title result is not saved just because it has lyrics.

## Device offset

The Now playing lyrics panel has **−0.1 / +0.1** controls and a reset button.
The offset is clamped to ±0.5 seconds and changes both the highlighted line and
the time used when you click a line to seek.

Each browser has a stable device ID. Its offset is stored in that user's
preferences, so it is included in the normal user backup but does not affect
another phone or computer. The audio file and `.lrc` sidecar are never rewritten
by this control.

## Kugou evaluation

Kugou was evaluated as an optional provider but is **not enabled** in this wave.
The usable search/download endpoints are public but undocumented, their fields
and signatures change with official client updates, and the content carries
copyright/region risk. LRCLIB's documented search fallback plus NetEase cover
the approved need without adding a default-on unofficial source.

## API

Both endpoints require an admin.

| Endpoint | What it does |
|---|---|
| `GET /api/lyrics/health` | Fresh read-only status report |
| `POST /api/lyrics/health/fill` | Fetch and write lyrics for `{files: [...]}`; maximum 100 paths |

See the [API reference](../api-reference.md#lyrics-health) for response shapes.
