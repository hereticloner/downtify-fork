---
icon: lucide/stethoscope
---

# Library Health

Library Health is the admin's read-only diagnostic page at `/library/health`.
It compares the audio files actually on disk with the TrackIndex, playlist
catalog, Playlist Monitor history and Navidrome mapping cache. Open it from
the **Health** button in the Library header.

The page never repairs, moves or deletes anything. Each finding names a safe
next step you can carry out with the existing maintenance tools.

## Running a scan

Press **Scan**. Downtify walks the configured library folders fresh rather
than using the warm Library listing, then reads the supporting stores. A large
library can take a little longer; the button reports progress by its loading
state.

The summary strip always shows all five categories, including zeroes. Use the
category chips to narrow the findings table. The live admin view may show
stored paths so you can identify the affected file.

## Finding categories

| Category | What it means | Safe next step |
|---|---|---|
| Missing file | A playlist, watch or referenced index row points to a file that is no longer on disk | Download the track again, or review the source record |
| Path mismatch | The old path is gone but a disk file has the same content key (basename + size) | Run Library path sync |
| Stale mapping | A Navidrome cache row points to a content key that is no longer on disk | Refresh Navidrome mappings |
| Missing metadata | A disk file has no title tag or no artist tag, even if its filename supplies a display fallback | Repair the track's tags |
| Orphan record | A TrackIndex row has no file and is not referenced by a playlist or watch | Review the record before removing it |

A missing file referenced by more than one store is shown once. A moved file
is reported as a path mismatch rather than a missing file when its content key
still matches.

## Export

**Export** downloads `downtify-library-health.json`. The exported report keeps
the scan time, source availability, category counts and finding codes, but
drops every stored path, filename, Spotify/Navidrome record ID and suggested
path. It is safe to attach to a support conversation without publishing the
shape of your library.

If a store cannot be read, the page reports a partial scan instead of failing
the whole report. A missing or unreadable downloads root is also partial
(`disk_unavailable`), never a clean bill of health. Exception text and paths
are not copied into warnings.

## API

Both endpoints require an admin session or admin device token.

| Endpoint | What it does |
|---|---|
| `GET /api/library/health` | Fresh read-only report with live admin paths and record IDs |
| `GET /api/library/health/export` | Redacted JSON attachment with counts and codes only |

See the [API reference](../api-reference.md#library-health) for the response
shape.
