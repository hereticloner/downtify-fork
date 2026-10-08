"""Storage report and duplicate cleanup.

Reads the library listing and the filesystem to answer two questions an
admin asks about a big local library:

* **How full is the disk?** — total/used/free space and the library's
  share of it.
* **What is duplicated?** — the same song (same artist + title, folded
  the way the Library page folds) downloaded more than once, so the
  copies can be deleted.

Duplicates are grouped by :func:`downtify.library_catalog.song_key`; the
best copy (largest file, then highest bitrate) is kept and the rest are
listed for deletion. Deleting removes the file and drops the library
cache so the next listing is clean.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from loguru import logger

from .library_catalog import (
    drop_library_listing_files,
    list_library_entries,
    resolve_library_file,
    song_key,
)


def disk_usage(path: Path) -> dict[str, Any]:
    """Total/used/free bytes and the used percentage for *path*."""

    try:
        usage = shutil.disk_usage(str(path))
    except OSError as exc:
        logger.warning('Could not stat disk {}: {}', path, exc)
        return {'total': 0, 'used': 0, 'free': 0, 'percent': 0}
    total = int(usage.total)
    used = int(usage.used)
    free = int(usage.free)
    percent = round(used * 100 / total, 1) if total else 0.0
    return {
        'total': total,
        'used': used,
        'free': free,
        'percent': percent,
    }


def library_size(ctx: Any) -> dict[str, Any]:
    """Total bytes and track count for the library on disk."""

    entries = list_library_entries(ctx)
    total = 0
    for entry in entries:
        try:
            total += int(entry.get('size') or 0)
        except (TypeError, ValueError):
            continue
    return {'bytes': total, 'tracks': len(entries)}


def find_duplicates(ctx: Any) -> list[dict[str, Any]]:
    """Songs downloaded more than once, grouped for cleanup.

    Each group keeps the best copy (largest file, then highest bitrate)
    and lists the rest as deletable. Groups with a single copy are
    skipped.
    """

    entries = list_library_entries(ctx)
    groups: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        artist = str(entry.get('artist') or '').strip()
        title = str(entry.get('title') or '').strip()
        if not artist or not title:
            continue
        key = song_key(artist, title)
        groups.setdefault(key, []).append(entry)

    duplicates: list[dict[str, Any]] = []
    for key, items in groups.items():
        if len(items) < 2:
            continue
        # Best copy first: largest file, then highest bitrate, then
        # earliest added (so the kept one is the original download).
        items.sort(
            key=lambda e: (
                -int(e.get('size') or 0),
                -int(e.get('bitrate') or 0),
                int(e.get('added') or 0),
            )
        )
        keep = items[0]
        rest = items[1:]
        duplicates.append({
            'key': key,
            'artist': str(keep.get('artist') or ''),
            'title': str(keep.get('title') or ''),
            'album': str(keep.get('album') or ''),
            'keep': {
                'file': str(keep.get('file') or ''),
                'size': int(keep.get('size') or 0),
            },
            'duplicates': [
                {
                    'file': str(e.get('file') or ''),
                    'size': int(e.get('size') or 0),
                }
                for e in rest
            ],
            'wasted_bytes': sum(int(e.get('size') or 0) for e in rest),
        })
    duplicates.sort(key=lambda g: -g['wasted_bytes'])
    return duplicates


def delete_files(ctx: Any, files: list[str]) -> dict[str, Any]:
    """Delete library files by their stored path.

    Returns how many were removed. A file that is already gone is not an
    error. The library cache is dropped so the next listing is clean.
    """

    removed = 0
    for stored in files:
        name = str(stored or '').strip().replace('\\', '/')
        if not name:
            continue
        full = resolve_library_file(name, ctx)
        if full is None or not full.is_file():
            continue
        try:
            full.unlink()
            removed += 1
        except OSError as exc:
            logger.warning('Could not delete {}: {}', full, exc)
    if removed:
        drop_library_listing_files(ctx)
    return {'removed': removed}
