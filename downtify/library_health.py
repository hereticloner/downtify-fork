"""Read-only diagnostics for the files and indexes that make up the library."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .library_cache_keys import file_content_key
from .library_catalog import LibraryContext, _scan_library_path_pairs
from .library_metadata import read_audio_metadata

CATEGORY_ORDER = (
    'missing_file',
    'path_mismatch',
    'stale_mapping',
    'missing_metadata',
    'orphan_record',
)

_SOURCE_ORDER = {'track_index': 0, 'playlist': 1, 'monitor': 2, 'navidrome': 3}


def _name(value: Any) -> str:
    return str(value or '').strip().replace('\\', '/')


def _disk_snapshot(
    ctx: LibraryContext,
) -> tuple[dict[str, Path], dict[str, str]]:
    by_path: dict[str, Path] = {}
    by_key: dict[str, str] = {}
    for stored, full in _scan_library_path_pairs(ctx):
        name = _name(stored)
        if not name:
            continue
        by_path[name] = Path(full)
        key = file_content_key(Path(full))
        if key:
            by_key[key] = name
    return by_path, by_key


def _finding(
    category: str,
    source: str,
    filename: str,
    record_id: str,
    recommendation: str,
    *,
    suggested_path: str = '',
) -> dict[str, Any]:
    row: dict[str, Any] = {
        'id': f'{source}:{record_id}:{filename}',
        'category': category,
        'severity': 'info'
        if category in {'path_mismatch', 'missing_metadata'}
        else 'warning',
        'source': source,
        'file': filename,
        'record_id': record_id,
        'recommendation': recommendation,
    }
    if suggested_path:
        row['suggested_path'] = suggested_path
    return row


def scan_library_health(
    ctx: LibraryContext,
    *,
    track_index: Any = None,
    playlist_catalog: Any = None,
    monitor_db: Any = None,
    navidrome_index: Any = None,
) -> dict[str, Any]:
    """Compare a fresh disk snapshot with the library's read-only stores."""

    disk_by_path, disk_by_key = _disk_snapshot(ctx)
    findings: dict[tuple[str, str, str], dict[str, Any]] = {}
    warnings: list[str] = []
    for name, full in disk_by_path.items():
        try:
            metadata = read_audio_metadata(full)
        except Exception:
            warnings.append('metadata_unavailable')
            continue
        if (
            str(metadata.get('title') or '').strip()
            and str(metadata.get('artist') or '').strip()
        ):
            continue
        key = file_content_key(full) or name
        findings[('missing_metadata', name, key)] = _finding(
            'missing_metadata', 'disk', name, key, 'repair_metadata'
        )
    track_rows: list[dict[str, Any]] = []
    playlist_rows: list[dict[str, Any]] = []
    monitor_rows: list[dict[str, Any]] = []
    navidrome_rows: list[dict[str, Any]] = []

    def read(source: str, reader: Any, target: list[dict[str, Any]]) -> None:
        try:
            target.extend(reader())
        except Exception:
            warnings.append(f'{source}_unavailable')

    if track_index is not None:
        read('track_index', track_index.all_rows, track_rows)
    if playlist_catalog is not None:
        read('playlist', playlist_catalog.all_track_rows, playlist_rows)
    if monitor_db is not None:
        read('monitor', monitor_db.list_all_downloaded_tracks, monitor_rows)
    if navidrome_index is not None:
        read('navidrome', navidrome_index.all_rows, navidrome_rows)

    referenced = {
        _name(row.get('track_spotify_id'))
        for row in [*playlist_rows, *monitor_rows]
        if _name(row.get('track_spotify_id'))
    }

    def add(row: dict[str, Any]) -> None:
        key = (row['category'], row['file'], row['record_id'])
        previous = findings.get(key)
        if (
            previous is None
            or _SOURCE_ORDER[row['source']] < _SOURCE_ORDER[previous['source']]
        ):
            findings[key] = row

    def classify(
        source: str, filename: str, record_id: str, content_key: str
    ) -> None:
        name = _name(filename)
        if not name:
            return
        if name in disk_by_path:
            return
        suggested = disk_by_key.get(_name(content_key))
        if suggested:
            add(
                _finding(
                    'path_mismatch',
                    source,
                    name,
                    record_id,
                    'reconcile_paths',
                    suggested_path=suggested,
                )
            )
            return
        if source == 'track_index' and record_id not in referenced:
            add(
                _finding(
                    'orphan_record',
                    source,
                    name,
                    record_id,
                    'review_record',
                )
            )
            return
        add(_finding('missing_file', source, name, record_id, 'redownload'))

    for row in track_rows:
        classify(
            'track_index',
            row.get('filename'),
            row.get('spotify_track_id'),
            row.get('content_key'),
        )
    for row in playlist_rows:
        classify(
            'playlist',
            row.get('filename'),
            row.get('track_spotify_id'),
            row.get('content_key'),
        )
    for row in monitor_rows:
        classify(
            'monitor',
            row.get('filename'),
            row.get('track_spotify_id'),
            '',
        )
    for row in navidrome_rows:
        if _name(row.get('content_key')) not in disk_by_key:
            add(
                _finding(
                    'stale_mapping',
                    'navidrome',
                    _name(row.get('filename')),
                    _name(row.get('navidrome_song_id')),
                    'refresh_navidrome',
                )
            )

    ordered = sorted(
        findings.values(),
        key=lambda row: (
            CATEGORY_ORDER.index(row['category']),
            row['source'],
            row['file'],
            row['record_id'],
        ),
    )
    by_category = {category: 0 for category in CATEGORY_ORDER}
    for row in ordered:
        by_category[row['category']] += 1
    return {
        'version': 1,
        'scanned_at': datetime.now(timezone.utc).isoformat(),
        'summary': {
            'disk_files': len(disk_by_path),
            'indexed_tracks': len(track_rows),
            'findings': len(ordered),
            'by_category': by_category,
        },
        'sources': {
            'disk': True,
            'track_index': track_index is not None
            and not any(
                warning == 'track_index_unavailable' for warning in warnings
            ),
            'playlist_catalog': playlist_catalog is not None
            and not any(
                warning == 'playlist_unavailable' for warning in warnings
            ),
            'monitor': monitor_db is not None
            and not any(
                warning == 'monitor_unavailable' for warning in warnings
            ),
            'navidrome': navidrome_index is not None
            and not any(
                warning == 'navidrome_unavailable' for warning in warnings
            ),
        },
        'findings': ordered,
        'warnings': warnings,
    }


def redact_health_report(report: dict[str, Any]) -> dict[str, Any]:
    """Keep diagnostic counts and codes, dropping every library identifier."""

    summary = report.get('summary') or {}
    sources = report.get('sources') or {}
    warning_codes = {
        'metadata_unavailable',
        'track_index_unavailable',
        'playlist_unavailable',
        'monitor_unavailable',
        'navidrome_unavailable',
    }
    findings = []
    for number, row in enumerate(report.get('findings') or [], start=1):
        findings.append({
            'id': number,
            'category': str(row.get('category') or ''),
            'severity': str(row.get('severity') or ''),
            'source': str(row.get('source') or ''),
            'recommendation': str(row.get('recommendation') or ''),
        })
    return {
        'version': int(report.get('version') or 1),
        'scanned_at': str(report.get('scanned_at') or ''),
        'summary': {
            'disk_files': int(summary.get('disk_files') or 0),
            'indexed_tracks': int(summary.get('indexed_tracks') or 0),
            'findings': int(summary.get('findings') or 0),
            'by_category': {
                category: int(
                    (summary.get('by_category') or {}).get(category) or 0
                )
                for category in CATEGORY_ORDER
            },
        },
        'sources': {
            key: bool(sources.get(key))
            for key in (
                'disk',
                'track_index',
                'playlist_catalog',
                'monitor',
                'navidrome',
            )
        },
        'findings': findings,
        'warnings': [
            str(warning)
            for warning in report.get('warnings') or []
            if str(warning) in warning_codes
        ],
    }
