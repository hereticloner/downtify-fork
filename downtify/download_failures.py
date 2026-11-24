"""Persistent download failures for the Queue's retry/exclude center."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .sqlite_utils import connect_sqlite


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_list(raw: Any) -> list[Any]:
    try:
        value = json.loads(raw or '[]')
    except (TypeError, ValueError):
        return []
    return value if isinstance(value, list) else []


class DownloadFailureStore:
    """One open failure per song, with merged retry context."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS download_failures (
                    song_id TEXT PRIMARY KEY,
                    song_json TEXT NOT NULL,
                    message TEXT NOT NULL,
                    code TEXT NOT NULL DEFAULT '',
                    provider TEXT NOT NULL DEFAULT '',
                    playlists_json TEXT NOT NULL DEFAULT '[]',
                    user_ids_json TEXT NOT NULL DEFAULT '[]',
                    attempts INTEGER NOT NULL DEFAULT 1,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    resolved_at TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS download_failures_open
                ON download_failures (resolved_at, last_seen DESC)
            """)

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._path, row_factory=True)

    def record(
        self,
        *,
        song_id: str,
        song: dict[str, Any],
        message: str,
        code: str = '',
        provider: str = '',
        playlist_name: str = '',
        user_ids: Optional[list[int]] = None,
    ) -> dict[str, Any]:
        sid = str(song_id)
        if not sid:
            raise ValueError('song_id is required')
        now = _now()
        playlists = _json_list(song.get('playlists_json'))
        users = _json_list(song.get('user_ids_json'))
        with self._connect() as conn:
            previous = conn.execute(
                'SELECT * FROM download_failures WHERE song_id=?', (sid,)
            ).fetchone()
            if previous is None:
                first_seen = now
                attempts = 1
                merged_playlists = playlists
                merged_users = users
            else:
                first_seen = previous['first_seen']
                attempts = int(previous['attempts']) + 1
                merged_playlists = sorted(
                    set(_json_list(previous['playlists_json']))
                    | set(playlists)
                )
                merged_users = sorted(
                    {int(uid) for uid in _json_list(previous['user_ids_json'])}
                    | {int(uid) for uid in users}
                )
            if playlist_name and playlist_name not in merged_playlists:
                merged_playlists = sorted([*merged_playlists, playlist_name])
            for uid in user_ids or []:
                if int(uid) and int(uid) not in merged_users:
                    merged_users = sorted([*merged_users, int(uid)])
            conn.execute(
                'INSERT INTO download_failures '
                '(song_id, song_json, message, code, provider, '
                'playlists_json, user_ids_json, attempts, first_seen, '
                'last_seen, resolved_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL) '
                'ON CONFLICT(song_id) DO UPDATE SET '
                'song_json=excluded.song_json, message=excluded.message, '
                'code=excluded.code, provider=excluded.provider, '
                'playlists_json=excluded.playlists_json, '
                'user_ids_json=excluded.user_ids_json, '
                'attempts=excluded.attempts, last_seen=excluded.last_seen, '
                'resolved_at=NULL',
                (
                    sid,
                    json.dumps(song, default=str),
                    str(message or '')[:1000],
                    str(code or '')[:100],
                    str(provider or '')[:100],
                    json.dumps(merged_playlists),
                    json.dumps(merged_users),
                    attempts,
                    first_seen,
                    now,
                ),
            )
            row = conn.execute(
                'SELECT * FROM download_failures WHERE song_id=?', (sid,)
            ).fetchone()
        return self._row(row)

    def resolve(self, song_id: str) -> bool:
        with self._connect() as conn:
            return (
                conn.execute(
                    'UPDATE download_failures SET resolved_at=? '
                    'WHERE song_id=? AND resolved_at IS NULL',
                    (_now(), str(song_id)),
                ).rowcount
                == 1
            )

    def list(
        self, limit: int = 100, include_resolved: bool = False
    ) -> list[dict[str, Any]]:
        where = '' if include_resolved else 'WHERE resolved_at IS NULL'
        with self._connect() as conn:
            rows = conn.execute(
                f'SELECT * FROM download_failures {where} '
                'ORDER BY last_seen DESC LIMIT ?',
                (max(1, int(limit)),),
            ).fetchall()
        return [self._row(row) for row in rows]

    def clear(self) -> int:
        with self._connect() as conn:
            return conn.execute(
                'DELETE FROM download_failures WHERE resolved_at IS NOT NULL'
            ).rowcount

    def forget_song(self, song_id: str) -> bool:
        with self._connect() as conn:
            return (
                conn.execute(
                    'DELETE FROM download_failures WHERE song_id=?',
                    (str(song_id),),
                ).rowcount
                == 1
            )

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        try:
            song = json.loads(row['song_json'])
        except (TypeError, ValueError):
            song = {}
        return {
            'song_id': row['song_id'],
            'song': song if isinstance(song, dict) else {},
            'message': row['message'],
            'code': row['code'],
            'provider': row['provider'],
            'playlists': _json_list(row['playlists_json']),
            'user_ids': [int(uid) for uid in _json_list(row['user_ids_json'])],
            'attempts': int(row['attempts']),
            'first_seen': row['first_seen'],
            'last_seen': row['last_seen'],
            'resolved_at': row['resolved_at'],
        }
