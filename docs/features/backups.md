---
icon: lucide/archive
---

# Backups

Downtify keeps two local, versioned `JSON.gz` snapshots under `/data/backups`.
They cover settings, notification secrets, account password hashes and
preferences, likes, playlists, Collections, watches, the saved download queue,
exclusions, trash metadata, playback history and activity. Audio files and
active sign-in sessions are never included.

Open **Settings → Server → Backups**.

## Create, download or upload

**Create backup** writes and verifies a snapshot atomically, then keeps the two
newest copies. **Download** saves the gzip file locally. **Upload** accepts a
`downtify-*.json.gz` file, validates it and applies the same two-copy rotation.

Automatic backups can be off, daily, every three days or weekly. The schedule
is stored in `/data/backup-schedule.json` and checked hourly.

## Restore safely

1. Press **Preview restore** and choose whether missing tracks with a stable
   Spotify id should be requeued.
2. Review the counts. Tracks without a stable id are listed as unresolved and
   are never guessed or downloaded.
3. Press **Restore** to confirm.

Restore is an **additive merge**: existing users, settings, watches, playlists
and collections are preserved; only missing records are added. A dry run
changes nothing. A backup must match the supported format version; corrupt or
future-version files are rejected.

## Secret warning

A backup contains password hashes, Telegram/ntfy/webhook secrets and other
account metadata. Backup files are written with mode `0600`, but they are not
encrypted. Store downloaded copies somewhere private. Remote destinations and
passphrase encryption are not part of this first version.
