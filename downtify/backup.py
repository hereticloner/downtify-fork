"""Versioned, atomic backups of Downtify metadata (never audio files)."""

from __future__ import annotations

import gzip
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import collections, monitor
from .download_queue import PendingDownloads
from .likes import LikedTracks
from .playback import PlaybackStore
from .playlist_catalog import PlaylistCatalog
from .track_index import TrackIndex
from .users import UserStore

BACKUP_VERSION = 1
KEEP_COPIES = 2

_SQLITE_TABLES: dict[str, tuple[str, ...]] = {
    'downtify.db': ('users', 'auth_config', 'auth_devices'),
    'downtify_library.db': (
        'library_tracks',
        'liked_tracks',
        'playlists',
        'playlist_tracks',
        'pending_downloads',
        'download_queue_state',
        'download_failures',
        'file_providers',
        'lyrics_lookups',
    ),
    'downtify_monitor.db': (
        'monitored_playlists',
        'downloaded_tracks',
        'seen_albums',
        'download_policy',
    ),
    'downtify_activity.db': (
        'playback_positions',
        'playback_events',
        'playback_daily',
        'activity',
    ),
}


_PRIMARY_KEYS: dict[str, tuple[str, ...]] = {
    'users': ('username',),
    'auth_config': ('key',),
    'auth_devices': ('id',),
    'library_tracks': ('spotify_track_id',),
    'liked_tracks': ('stored_path',),
    'playlists': ('name',),
    'playlist_tracks': ('playlist_name', 'track_spotify_id'),
    'pending_downloads': ('song_id',),
    'download_queue_state': ('key',),
    'download_failures': ('song_id',),
    'file_providers': ('filename',),
    'lyrics_lookups': ('cache_key',),
    'monitored_playlists': ('spotify_id',),
    'downloaded_tracks': ('playlist_id', 'track_spotify_id'),
    'seen_albums': ('playlist_id', 'album_id'),
    'download_policy': ('id',),
    'playback_positions': ('user_id', 'device_id', 'track_key'),
    'playback_events': ('id',),
    'playback_daily': ('user_id', 'day'),
    'activity': ('id',),
}


def _ensure_table(conn: sqlite3.Connection, table: str) -> None:
    columns = {row[1] for row in conn.execute(f'PRAGMA table_info({table})')}
    if not columns:
        raise ValueError(f'backup table {table} is unavailable')
    return columns


def _insert_missing(
    conn: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
    keys: tuple[str, ...],
) -> int:
    if not rows:
        return 0
    available = _ensure_table(conn, table)
    added = 0
    for row in rows:
        if not keys or any(key not in row for key in keys):
            continue
        where = ' AND '.join(f'{key}=?' for key in keys)
        if (
            conn.execute(
                f'SELECT 1 FROM {table} WHERE {where}',
                tuple(row[key] for key in keys),
            ).fetchone()
            is not None
        ):
            continue
        fields = [key for key in row if key in available]
        if not fields:
            continue
        names = ','.join(fields)
        marks = ','.join('?' for _ in fields)
        values = []
        for field in fields:
            value = row[field]
            if isinstance(value, (dict, list)):
                value = json.dumps(value, default=str)
            values.append(value)
        conn.execute(
            f'INSERT OR IGNORE INTO {table} ({names}) VALUES ({marks})',
            tuple(values),
        )
        added += 1
    return added


def _queue_identity(
    rows: list[Any], *, requeue_missing: bool
) -> tuple[list[str], list[str]]:
    requeued: list[str] = []
    unresolved: list[str] = []
    if not requeue_missing:
        return requeued, unresolved
    for row in rows:
        if not isinstance(row, dict):
            continue
        song_id = str(row.get('song_id') or '')
        song = row.get('song')
        if isinstance(song, str):
            try:
                song = json.loads(song)
            except ValueError:
                song = {}
        stable = bool(
            song_id
            and re.fullmatch(r'[A-Za-z0-9]{22}', song_id)
            and isinstance(song, dict)
            and song.get('song_id') == song_id
        )
        if stable:
            requeued.append(song_id)
        elif song_id:
            unresolved.append(song_id)
    return requeued, unresolved


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def _json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def _ensure_schema(filename: str, data_dir: Path) -> None:
    if filename == 'downtify.db':
        UserStore(data_dir / filename)
    elif filename == 'downtify_library.db':
        TrackIndex(data_dir / filename)
        LikedTracks(data_dir / filename)
        PlaylistCatalog(data_dir / filename)
        PendingDownloads(data_dir / filename)
    elif filename == 'downtify_monitor.db':
        monitor.PlaylistMonitorDB(data_dir / filename)
    elif filename == 'downtify_activity.db':
        PlaybackStore(data_dir / filename)


def _atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f'.{path.name}.partial')
    payload = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(partial, path)
        path.chmod(0o600)
    finally:
        partial.unlink(missing_ok=True)


def _read_backup(path: Path) -> dict[str, Any]:
    try:
        with gzip.open(path, 'rt', encoding='utf-8') as handle:
            doc = json.load(handle)
    except (OSError, ValueError, EOFError) as exc:
        raise ValueError('corrupt backup') from exc
    if not isinstance(doc, dict) or doc.get('version') != BACKUP_VERSION:
        raise ValueError('unsupported backup version')
    if not isinstance(doc.get('sqlite'), dict):
        raise ValueError('corrupt backup')
    return doc


def _validated_backup_path(store: BackupStore, path: Path) -> Path:
    path = Path(path)
    if (
        path.parent != store.backup_dir
        or not path.name.startswith('downtify-')
        or not path.name.endswith('.json.gz')
    ):
        raise ValueError('invalid backup path')
    return path


def _table_rows(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    columns = {row[1] for row in conn.execute(f'PRAGMA table_info({table})')}
    if not columns:
        return []
    rows = conn.execute(f'SELECT * FROM {table}').fetchall()
    return [dict(row) for row in rows]


class BackupStore:
    """Write, inspect and additively restore local ``backups/*.json.gz``."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.backup_dir = self.data_dir / 'backups'

    def _snapshot(self) -> dict[str, Any]:
        sqlite: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for filename, tables in _SQLITE_TABLES.items():
            path = self.data_dir / filename
            if not path.is_file():
                continue
            conn = sqlite3.connect(path)
            conn.row_factory = sqlite3.Row
            try:
                sqlite[filename] = {
                    table: _table_rows(conn, table) for table in tables
                }
            finally:
                conn.close()
        downloads = self.data_dir / 'downloads'
        return {
            'version': BACKUP_VERSION,
            'created_at': _now(),
            'settings': _json_file(self.data_dir / 'settings.json') or {},
            'notification_secrets': _json_file(
                self.data_dir / 'notifications.json'
            )
            or {'version': 1},
            'sqlite': sqlite,
            'collections': collections.list_collections(downloads),
        }

    def write(self) -> Path:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
        target = self.backup_dir / f'downtify-{stamp}.json.gz'
        partial = target.with_name(f'.{target.name}.partial')
        payload = json.dumps(
            self._snapshot(), ensure_ascii=False, separators=(',', ':')
        ).encode('utf-8')
        fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, 'wb') as handle:
                with gzip.GzipFile(fileobj=handle, mode='wb') as zipped:
                    zipped.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            with gzip.open(partial, 'rb') as handle:
                if json.loads(handle.read()) != json.loads(payload):
                    raise ValueError('backup failed read-back')
            os.replace(partial, target)
            target.chmod(0o600)
        finally:
            partial.unlink(missing_ok=True)
        for old in self.list()[KEEP_COPIES:]:
            old.unlink(missing_ok=True)
        return target

    def list(self) -> list[Path]:
        if not self.backup_dir.is_dir():
            return []
        return sorted(
            self.backup_dir.glob('downtify-*.json.gz'),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )

    def preview(self, path: Path) -> dict[str, Any]:
        path = Path(path)
        if path.parent == self.backup_dir:
            path = _validated_backup_path(self, path)
        return _read_backup(path)

    def restore(
        self,
        path: Path,
        *,
        dry_run: bool = True,
        requeue_missing: bool = False,
    ) -> dict[str, Any]:
        doc = self.preview(path)
        added: dict[str, int] = {}
        requeued: list[str] = []
        unresolved: list[str] = []
        for filename, tables in doc['sqlite'].items():
            if filename not in _SQLITE_TABLES:
                continue
            for table, rows in tables.items():
                if table not in _SQLITE_TABLES[filename] or not isinstance(
                    rows, list
                ):
                    continue
                keys = _PRIMARY_KEYS.get(table, ())
                if table == 'pending_downloads':
                    found, missing = _queue_identity(
                        rows, requeue_missing=requeue_missing
                    )
                    requeued.extend(found)
                    unresolved.extend(missing)
                if dry_run:
                    target = self.data_dir / filename
                    if not target.is_file():
                        added[table] = len(rows)
                        continue
                    conn = sqlite3.connect(target)
                    conn.row_factory = sqlite3.Row
                    try:
                        existing = (
                            {
                                tuple(row[key] for key in keys)
                                for row in _table_rows(conn, table)
                            }
                            if keys
                            else set()
                        )
                        count = sum(
                            1
                            for row in rows
                            if isinstance(row, dict)
                            and keys
                            and all(key in row for key in keys)
                            and tuple(row[key] for key in keys) not in existing
                        )
                        added[table] = count
                    finally:
                        conn.close()
                    continue
                self.data_dir.mkdir(parents=True, exist_ok=True)
                _ensure_schema(filename, self.data_dir)
                conn = sqlite3.connect(self.data_dir / filename)
                conn.row_factory = sqlite3.Row
                try:
                    with conn:
                        count = _insert_missing(
                            conn,
                            table,
                            [row for row in rows if isinstance(row, dict)],
                            keys,
                        )
                    added[table] = count
                finally:
                    conn.close()

        collection_count = 0
        existing_collections = {
            item['name'].casefold(): item
            for item in collections.list_collections(
                self.data_dir / 'downloads'
            )
        }
        for item in doc.get('collections') or []:
            if not isinstance(item, dict) or not item.get('name'):
                continue
            name = str(item['name'])
            if name.casefold() in existing_collections:
                continue
            collection_count += 1
            if not dry_run:
                path_out = (
                    self.data_dir
                    / 'downloads'
                    / 'Playlists'
                    / '.collections'
                    / f'{name}.json'
                )
                path_out.parent.mkdir(parents=True, exist_ok=True)
                path_out.write_text(
                    json.dumps(item, ensure_ascii=False, indent=2)
                )
        added['collections'] = collection_count

        if not dry_run:
            settings = doc.get('settings')
            if isinstance(settings, dict) and settings:
                _atomic_json(self.data_dir / 'settings.json', settings)
            secrets = doc.get('notification_secrets')
            if isinstance(secrets, dict) and secrets:
                _atomic_json(self.data_dir / 'notifications.json', secrets)
        return {
            'dry_run': dry_run,
            'added': added,
            'requeued': sorted(set(requeued)),
            'unresolved': sorted(set(unresolved)),
        }
