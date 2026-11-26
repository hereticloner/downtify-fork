"""Versioned, atomic backups of Downtify metadata (never audio files)."""

from __future__ import annotations

import base64
import gzip
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import (
    collections,
    lastfm_history,
    m3u,
    monitor,
    notifications,
    playlist_mosaic,
    spotify_context,
    spotify_history,
)
from .download_queue import PendingDownloads
from .likes import LikedTracks
from .listening_history import ListeningStore
from .playback import PlaybackStore
from .playlist_catalog import PlaylistCatalog
from .track_index import TrackIndex
from .users import UserStore

BACKUP_VERSION = 1
KEEP_COPIES = 2
MAX_BACKUP_BYTES = 256 * 1024 * 1024

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
        'listening_events',
        'listening_event_sources',
        'spotify_recently_played',
        'lastfm_recent_tracks',
        'history_import_state',
        'spotify_context_cache',
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
    'listening_events': ('id',),
    'listening_event_sources': ('event_id', 'source'),
    'spotify_recently_played': ('source_key',),
    'lastfm_recent_tracks': ('source_key',),
    'history_import_state': ('source',),
    'spotify_context_cache': ('context_key',),
}


def _ensure_table(conn: sqlite3.Connection, table: str) -> set[str]:
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


def _known_library_files(
    data_dir: Path, doc: dict[str, Any]
) -> dict[str, str]:
    known: dict[str, str] = {}
    target = data_dir / 'downtify_library.db'
    if target.is_file():
        conn = sqlite3.connect(target)
        conn.row_factory = sqlite3.Row
        try:
            for row in _table_rows(conn, 'library_tracks'):
                known[str(row.get('spotify_track_id') or '')] = str(
                    row.get('filename') or ''
                )
        finally:
            conn.close()
    for row in (doc.get('sqlite') or {}).get('downtify_library.db', {}).get(
        'library_tracks', []
    ) or []:
        if isinstance(row, dict):
            known.setdefault(
                str(row.get('spotify_track_id') or ''),
                str(row.get('filename') or ''),
            )
    return known


def _file_exists(data_dir: Path, filename: str) -> bool:
    relative = Path(filename)
    if not filename or relative.is_absolute() or '..' in relative.parts:
        return False
    return (data_dir / 'downloads' / relative).is_file()


def _queue_restore_plan(
    rows: list[Any],
    *,
    requeue_missing: bool,
    known_files: dict[str, str],
    data_dir: Path,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    if not requeue_missing:
        return [row for row in rows if isinstance(row, dict)], [], []
    kept: list[dict[str, Any]] = []
    requeued: list[str] = []
    unresolved: list[str] = []
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
        if not stable:
            if song_id:
                unresolved.append(song_id)
            continue
        filename = known_files.get(song_id) or ''
        if _file_exists(data_dir, filename):
            continue
        if row.get('paused') in {1, True, '1'}:
            kept.append(row)
            continue
        kept.append(row)
        requeued.append(song_id)
    return kept, requeued, unresolved


def _collection_covers(download_dir: Path) -> dict[str, str]:
    covers = Path(download_dir) / 'Playlists' / '.collections' / 'covers'
    if not covers.is_dir():
        return {}
    return {
        path.stem: base64.b64encode(path.read_bytes()).decode('ascii')
        for path in covers.glob('*.jpg')
        if path.is_file()
        and m3u.sanitize_playlist_name(path.stem) == path.stem
    }


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
        ListeningStore(data_dir / filename)
        spotify_history.ensure_schema(data_dir / filename)
        lastfm_history.ensure_schema(data_dir / filename)
        spotify_context.ensure_schema(data_dir / filename)


def _merge_missing(existing: Any, incoming: Any) -> Any:
    """Deep merge where every existing scalar/list value wins."""

    if isinstance(existing, dict) and isinstance(incoming, dict):
        merged = dict(existing)
        for key, value in incoming.items():
            if key not in merged:
                merged[key] = value
            elif isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = _merge_missing(merged[key], value)
        return merged
    return existing


def _restore_json_file(path: Path, incoming: dict[str, Any]) -> bool:
    existing = _json_file(path)
    if not isinstance(existing, dict):
        existing = {}
    merged = _merge_missing(existing, incoming)
    if merged == existing:
        return False
    _atomic_json(path, merged)
    return True


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f'.{path.name}.partial')
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


def _atomic_json(path: Path, data: dict[str, Any]) -> None:
    _atomic_bytes(
        path,
        json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'),
    )


class BackupTooLarge(ValueError):
    """The decompressed JSON exceeds the safe in-memory limit."""


def _read_backup(path: Path) -> dict[str, Any]:
    try:
        with gzip.open(path, 'rb') as handle:
            payload = handle.read(MAX_BACKUP_BYTES + 1)
        if len(payload) > MAX_BACKUP_BYTES:
            raise BackupTooLarge('backup too large')
        doc = json.loads(payload)
    except BackupTooLarge:
        raise
    except (OSError, ValueError, EOFError) as exc:
        raise ValueError('corrupt backup') from exc
    if not isinstance(doc, dict) or doc.get('version') != BACKUP_VERSION:
        raise ValueError('unsupported backup version')
    if not isinstance(doc.get('sqlite'), dict) or not all(
        isinstance(tables, dict) for tables in doc['sqlite'].values()
    ):
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


def _decode_collection_covers(doc: dict[str, Any]) -> dict[str, bytes]:
    raw = doc.get('collection_covers')
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError('corrupt backup')
    out: dict[str, bytes] = {}
    for name, encoded in raw.items():
        if (
            not isinstance(name, str)
            or m3u.sanitize_playlist_name(name) != name
            or Path(name).name != name
            or not isinstance(encoded, str)
        ):
            raise ValueError('corrupt backup')
        try:
            data = base64.b64decode(encoded, validate=True)
        except ValueError as exc:
            raise ValueError('corrupt backup') from exc
        if not data or len(data) > playlist_mosaic.MAX_PLAYLIST_COVER_BYTES:
            raise ValueError('corrupt backup')
        out[name] = data
    return out


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
            'collection_covers': _collection_covers(downloads),
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

    @staticmethod
    def preview(path: Path) -> dict[str, Any]:
        return _read_backup(Path(path))

    @staticmethod
    def validate_upload(path: Path) -> dict[str, Any]:
        return _read_backup(Path(path))

    def restore(
        self,
        path: Path,
        *,
        dry_run: bool = True,
        requeue_missing: bool = False,
    ) -> dict[str, Any]:
        doc = self.preview(path)
        cover_payloads = _decode_collection_covers(doc)
        added: dict[str, int] = {}
        requeued: list[str] = []
        unresolved: list[str] = []
        known_files = _known_library_files(self.data_dir, doc)
        for filename, tables in doc['sqlite'].items():
            if filename not in _SQLITE_TABLES:
                continue
            allowed = {
                table: rows
                for table, rows in tables.items()
                if table in _SQLITE_TABLES[filename] and isinstance(rows, list)
            }
            if 'pending_downloads' in allowed:
                allowed['pending_downloads'], found, missing = (
                    _queue_restore_plan(
                        allowed['pending_downloads'],
                        requeue_missing=requeue_missing,
                        known_files=known_files,
                        data_dir=self.data_dir,
                    )
                )
                requeued.extend(found)
                unresolved.extend(missing)
            if dry_run:
                for table, rows in allowed.items():
                    keys = _PRIMARY_KEYS.get(table, ())
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
                        added[table] = sum(
                            1
                            for row in rows
                            if isinstance(row, dict)
                            and keys
                            and all(key in row for key in keys)
                            and tuple(row[key] for key in keys) not in existing
                        )
                    finally:
                        conn.close()
                continue

            self.data_dir.mkdir(parents=True, exist_ok=True)
            _ensure_schema(filename, self.data_dir)
            conn = sqlite3.connect(self.data_dir / filename)
            conn.row_factory = sqlite3.Row
            try:
                with conn:
                    for table, rows in allowed.items():
                        keys = _PRIMARY_KEYS.get(table, ())
                        added[table] = _insert_missing(
                            conn,
                            table,
                            [row for row in rows if isinstance(row, dict)],
                            keys,
                        )
            finally:
                conn.close()

        collection_count = 0
        invalid_collections: list[str] = []
        existing_collections = {
            item['name'].casefold(): item
            for item in collections.list_collections(
                self.data_dir / 'downloads'
            )
        }
        collection_writes: list[tuple[Path, dict[str, Any]]] = []
        for item in doc.get('collections') or []:
            if not isinstance(item, dict) or not item.get('name'):
                continue
            name = str(item['name'])
            if (
                m3u.sanitize_playlist_name(name) != name
                or Path(name).name != name
            ):
                invalid_collections.append(name)
                continue
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
                collection_writes.append((path_out, item))
        added['collections'] = collection_count

        if not dry_run:
            settings = doc.get('settings')
            secrets = doc.get('notification_secrets')
            settings_path = self.data_dir / 'settings.json'
            secrets_path = self.data_dir / 'notifications.json'
            originals = {
                settings_path: settings_path.read_bytes()
                if settings_path.exists()
                else None,
                secrets_path: secrets_path.read_bytes()
                if secrets_path.exists()
                else None,
            }
            created_collections: list[Path] = []
            created_covers: list[Path] = []
            try:
                if isinstance(secrets, dict) and secrets:
                    _restore_json_file(secrets_path, secrets)
                if isinstance(settings, dict) and settings:
                    existing = _json_file(settings_path)
                    merged = _merge_missing(
                        existing if isinstance(existing, dict) else {},
                        settings,
                    )
                    block = merged.get('notifications')
                    if isinstance(block, dict) and (
                        any(
                            key in block
                            for key in (
                                'telegram_bot_token',
                                'telegram_chat_id',
                            )
                        )
                        or any(
                            field in config
                            for config in (
                                block.get('channels') or {}
                            ).values()
                            if isinstance(config, dict)
                            for field in (
                                'bot_token',
                                'chat_id',
                                'url',
                                'token',
                            )
                        )
                    ):
                        merged['notifications'] = notifications.clean_settings(
                            block,
                            _json_file(secrets_path)
                            if isinstance(_json_file(secrets_path), dict)
                            else secrets,
                        )
                    if merged != (
                        existing if isinstance(existing, dict) else {}
                    ):
                        _atomic_json(settings_path, merged)
                for path_out, item in collection_writes:
                    path_out.parent.mkdir(parents=True, exist_ok=True)
                    created_collections.append(path_out)
                    _atomic_json(path_out, item)
                covers_dir = (
                    self.data_dir
                    / 'downloads'
                    / 'Playlists'
                    / '.collections'
                    / 'covers'
                )
                for name, data in cover_payloads.items():
                    path_out = covers_dir / f'{name}.jpg'
                    if path_out.exists():
                        continue
                    _atomic_bytes(path_out, data)
                    created_covers.append(path_out)
            except Exception:
                for json_path, original in originals.items():
                    if original is None:
                        json_path.unlink(missing_ok=True)
                    else:
                        _atomic_bytes(json_path, original)
                for collection_path in created_collections:
                    collection_path.unlink(missing_ok=True)
                for cover_path in created_covers:
                    cover_path.unlink(missing_ok=True)
                raise
        return {
            'dry_run': dry_run,
            'added': added,
            'requeued': sorted(set(requeued)),
            'unresolved': sorted(set(unresolved)),
            'invalid_collections': sorted(set(invalid_collections)),
        }
