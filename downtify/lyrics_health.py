"""Read-only lyrics health report for the library."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from . import lyrics as lyrics_mod
from .library_catalog import (
    LibraryContext,
    _scan_library_path_pairs,
    resolve_library_file,
)
from .library_metadata import read_audio_metadata
from .lyrics import looks_like_lrc, read_track_lyrics
from .lyrics_cache import song_key
from .track_index import TrackIndex


def _stored_name(value: Any) -> str:
    return str(value or '').strip().replace('\\', '/')


def _path_available(path: Path) -> bool:
    try:
        return path.is_dir() and os.access(path, os.R_OK | os.X_OK)
    except OSError:
        return False


def _song_for_file(
    stored: str, full: Path, track_index: Optional[TrackIndex]
) -> dict[str, Any]:
    metadata = read_audio_metadata(full)
    artists = metadata.get('artists') or [
        part.strip()
        for part in str(metadata.get('artist') or '').split(',')
        if part.strip()
    ]
    song: dict[str, Any] = {
        'name': str(metadata.get('title') or '').strip(),
        'artists': [
            str(part).strip() for part in artists if str(part).strip()
        ],
        'album_name': str(metadata.get('album') or '').strip(),
        'duration': float(metadata.get('duration') or 0),
    }
    if track_index is not None:
        spotify_id = track_index.spotify_id_for_filename(stored)
        if spotify_id:
            song['song_id'] = spotify_id
    return song


def _lyrics_status(existing: dict[str, str]) -> str:
    synced = str(existing.get('synced') or '').strip()
    plain = str(existing.get('plain') or '').strip()
    if synced and looks_like_lrc(synced):
        return 'synced'
    if plain:
        return 'plain_only'
    return 'missing'


def scan_lyrics_health(
    ctx: LibraryContext,
    track_index: Optional[TrackIndex] = None,
) -> dict[str, Any]:
    """Compare disk tracks with their saved sidecar/embedded lyrics."""

    findings: list[dict[str, Any]] = []
    summary = {'tracks': 0, 'synced': 0, 'plain_only': 0, 'missing': 0}
    warnings: list[str] = []
    disk_available = _path_available(ctx.download_dir)
    if not disk_available:
        warnings.append('disk_unavailable')
    elif any(not _path_available(path) for path in ctx.extra_dirs):
        warnings.append('external_folder_unavailable')
    for stored, full in _scan_library_path_pairs(ctx):
        name = _stored_name(stored)
        if not name:
            continue
        path = Path(full)
        existing = read_track_lyrics(path)
        status = _lyrics_status(existing)
        song = _song_for_file(name, path, track_index)
        findings.append({
            'file': name,
            'status': status,
            'title': song['name'],
            'artist': ', '.join(song['artists']),
            'album': song['album_name'],
            'duration': song['duration'],
            'spotify_id': str(song.get('song_id') or ''),
        })
        summary['tracks'] += 1
        summary[status] += 1
    findings.sort(key=lambda row: row['file'])
    return {
        'version': 1,
        'scanned_at': datetime.now(timezone.utc).isoformat(),
        'summary': summary,
        'findings': findings,
        'sources': {'disk': not warnings},
        'warnings': warnings,
    }


def fill_lyrics(
    files: list[str],
    ctx: LibraryContext,
    settings: dict[str, Any],
    cache: Any,
    track_index: Optional[TrackIndex] = None,
) -> dict[str, Any]:
    """Fetch and write lyrics for explicitly requested library files."""

    names = list(
        dict.fromkeys(
            _stored_name(name) for name in files if _stored_name(name)
        )
    )
    result: dict[str, Any] = {
        'requested': len(names),
        'found': 0,
        'written': 0,
        'skipped': 0,
        'failed': 0,
        'errors': [],
    }
    providers = lyrics_mod.providers_from_settings(settings)
    if not providers:
        result['failed'] = len(names)
        result['errors'] = [
            {'file': name, 'code': 'lyrics_disabled'} for name in names
        ]
        return result
    synced_only = bool(settings.get('lyrics_synced_only', False))
    for position, name in enumerate(names):
        if position:
            time.sleep(0.25)
        full = resolve_library_file(name, ctx)
        if full is None:
            result['failed'] += 1
            result['errors'].append({'file': name, 'code': 'invalid_path'})
            continue
        try:
            status = _lyrics_status(read_track_lyrics(full))
            if status == 'synced' or (
                status == 'plain_only' and not synced_only
            ):
                result['skipped'] += 1
                continue
            song = _song_for_file(name, full, track_index)
            if cache is not None:
                cache.forget(song_key(song))
            found = lyrics_mod.fetch(
                song,
                providers,
                cache,
                synced_only=synced_only,
            )
            if found is None or not found.has_any():
                result['skipped'] += 1
                continue
            result['found'] += 1
            lyrics_mod.write_to_file(full, found)
            after = _lyrics_status(read_track_lyrics(full))
            if after == 'synced' or (
                after == 'plain_only' and not synced_only
            ):
                result['written'] += 1
            else:
                result['failed'] += 1
                result['errors'].append({'file': name, 'code': 'write_failed'})
        except Exception:
            result['failed'] += 1
            result['errors'].append({'file': name, 'code': 'lyrics_failed'})
    return result
