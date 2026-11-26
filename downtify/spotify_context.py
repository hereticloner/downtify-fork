"""Spotify playback-context parsing and persistent display-name cache."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from .sqlite_utils import connect_sqlite

TABLE = 'spotify_context_cache'
_KINDS = {'playlist', 'artist', 'album'}

_CREATE_TABLE = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    context_key TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    fetched_at TEXT NOT NULL DEFAULT '',
    last_error TEXT NOT NULL DEFAULT '',
    retry_at TEXT NOT NULL DEFAULT ''
)
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _valid_id(value: str) -> str:
    candidate = str(value or '').strip()
    if not candidate or '/' in candidate or ':' in candidate:
        return ''
    return candidate


def normalize_context(value: Any) -> str:
    """Normalize supported Spotify URI/URL forms to ``spotify:kind:id``."""

    raw = str(value or '').strip()
    if not raw:
        return ''
    if raw.startswith('spotify:'):
        parts = raw.split(':')
        if (
            len(parts) >= 4
            and parts[1] == 'user'
            and parts[2]
            and parts[3] in _KINDS
        ):
            kind, resource_id = (
                parts[3],
                _valid_id(parts[4] if len(parts) > 4 else ''),
            )
        elif len(parts) >= 3 and parts[1] in _KINDS:
            kind, resource_id = parts[1], _valid_id(':'.join(parts[2:]))
        else:
            return ''
        return f'spotify:{kind}:{resource_id}' if resource_id else ''
    parsed = urlparse(raw)
    host = (parsed.hostname or '').lower()
    parts = [part for part in parsed.path.split('/') if part]
    if host == 'api.spotify.com':
        kind = parts[1].rstrip('s') if len(parts) >= 3 else ''
        if len(parts) >= 3 and parts[0] == 'v1' and kind in _KINDS:
            resource_id = _valid_id(parts[2])
        else:
            return ''
    elif host == 'open.spotify.com':
        if parts and parts[0].startswith('intl-'):
            parts = parts[1:]
        if len(parts) >= 2 and parts[0] in _KINDS:
            kind, resource_id = parts[0], _valid_id(parts[1])
        else:
            return ''
    else:
        return ''
    return f'spotify:{kind}:{resource_id}' if resource_id else ''


def context_kind(value: Any) -> str:
    key = normalize_context(value)
    return key.split(':')[1] if key else ''


def ensure_schema(db_path: Any) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect_sqlite(str(path)) as conn:
        conn.execute(_CREATE_TABLE)


def cache_name(db_path: Any, context_key: str, name: str) -> None:
    key = normalize_context(context_key)
    display = str(name or '').strip()
    if not key or not display:
        return
    ensure_schema(db_path)
    with connect_sqlite(str(db_path)) as conn:
        conn.execute(
            f'INSERT INTO {TABLE} '
            '(context_key, kind, name, fetched_at, last_error, retry_at) '
            "VALUES (?, ?, ?, ?, '', '') "
            'ON CONFLICT(context_key) DO UPDATE SET '
            'name=excluded.name, fetched_at=excluded.fetched_at, '
            "last_error='', retry_at=''",
            (key, context_kind(key), display, _now()),
        )


def labels_for(db_path: Any, values: Iterable[Any]) -> dict[str, str]:
    wanted = {key for value in values if (key := normalize_context(value))}
    if not wanted or not Path(db_path).is_file():
        return {}
    try:
        with connect_sqlite(str(db_path), row_factory=True) as conn:
            rows = conn.execute(
                f"SELECT context_key, name FROM {TABLE} WHERE name != ''"
            ).fetchall()
    except sqlite3.Error:
        return {}
    return {
        str(row['context_key']): str(row['name'])
        for row in rows
        if str(row['context_key']) in wanted and str(row['name'] or '').strip()
    }
