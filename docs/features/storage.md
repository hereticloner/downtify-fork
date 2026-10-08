---
icon: lucide/hard-drive
---

# Storage

Downtify can show how full the download disk is and which songs sit on it
twice, so a big library stays worth keeping. It is a Settings section for
admins: **Settings → Storage**.

## Disk usage

The report opens when you open the section. It shows the disk the library
lives on (the downloads folder):

* **Used** — how much of the disk is taken, with a bar and a percentage.
* **Free** and **Total**.
* **Library size** — the audio files' total size and track count.

Press **Refresh** to read it again after a download or a cleanup.

## Duplicates

The same song can end up on disk twice — a playlist and an album download
of the same track, a re-download after a tag fix, a watch that grabbed a
song the library already had. The duplicate report groups those:

* Songs are matched by artist + title, folded the same way the Library
  page's filter folds (case, accents, `(feat. …)`/`(remaster)` tails).
* In each group the **best copy is kept**: largest file, then highest
  bitrate, then the earliest download.
* The rest are listed with their sizes, and the group shows how much
  space the extra copies **waste**.
* Groups are sorted by wasted space, biggest first.
* Songs without both an artist and a title tag are skipped — they cannot
  be matched safely.

Press **Delete duplicates** to remove every listed extra copy at once
(each group's kept copy survives). Downtify deletes the files and drops
the library cache, so the next Library listing is clean. The report then
refreshes itself.

Nothing is deleted until you press the button: the report only reads.

## API

* `GET /api/storage/report` — `{disk: {total, used, free, percent},
  library: {bytes, tracks}}`.
* `GET /api/storage/duplicates` — `{groups: [{key, artist, title, album,
  keep: {file, size}, duplicates: [{file, size}], wasted_bytes}],
  total_wasted_bytes}`.
* `POST /api/storage/duplicates/delete` — body `{files: [stored path,
  ...]}`; returns `{removed}`.

See the [API reference](../api-reference.md).