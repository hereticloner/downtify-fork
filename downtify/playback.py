"""Persistent playback positions and measured listening history."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from .sqlite_utils import connect_sqlite


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _track_key(track: dict[str, Any]) -> str:
    return str(track.get('track_id') or track.get('file') or '').strip()


class PlaybackStore:
    """Per-user, per-device playback state in the activity database."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS playback_positions (
                    user_id INTEGER NOT NULL,
                    device_id TEXT NOT NULL,
                    player TEXT NOT NULL,
                    track_key TEXT NOT NULL,
                    track_json TEXT NOT NULL,
                    position REAL NOT NULL,
                    max_position REAL NOT NULL DEFAULT 0,
                    duration REAL NOT NULL,
                    state TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, device_id, track_key)
                )
            """)
            columns = {
                row[1]
                for row in conn.execute(
                    'PRAGMA table_info(playback_positions)'
                )
            }
            if 'max_position' not in columns:
                conn.execute(
                    'ALTER TABLE playback_positions ADD COLUMN '
                    'max_position REAL NOT NULL DEFAULT 0'
                )
                conn.execute(
                    'UPDATE playback_positions SET max_position = position'
                )
            if 'completed_at' not in columns:
                conn.execute(
                    'ALTER TABLE playback_positions ADD COLUMN completed_at TEXT'
                )
            conn.execute("""
                CREATE TABLE IF NOT EXISTS playback_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    device_id TEXT NOT NULL,
                    player TEXT NOT NULL,
                    track_key TEXT NOT NULL,
                    track_json TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    position REAL NOT NULL,
                    duration REAL NOT NULL,
                    seconds REAL NOT NULL,
                    at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS playback_daily (
                    user_id INTEGER NOT NULL,
                    day TEXT NOT NULL,
                    seconds REAL NOT NULL DEFAULT 0,
                    plays INTEGER NOT NULL DEFAULT 0,
                    completions INTEGER NOT NULL DEFAULT 0,
                    skips INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (user_id, day)
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._path, row_factory=True)

    def report(
        self,
        *,
        user_id: int,
        device_id: str,
        player: str,
        state: str,
        track: dict[str, Any],
        position: float,
        seek: bool = False,
    ) -> dict[str, Any]:
        now = _now()
        day = now[:10]
        pos = max(0.0, float(position or 0))
        with self._connect() as conn:
            current = conn.execute(
                'SELECT * FROM playback_positions WHERE '
                'user_id=? AND device_id=? ORDER BY updated_at DESC LIMIT 1',
                (user_id, device_id),
            ).fetchone()
            key = _track_key(track)
            if state == 'stopped' and not key and current is not None:
                key = current['track_key']
                track = json.loads(current['track_json'])
            previous = None
            if key:
                previous = conn.execute(
                    'SELECT * FROM playback_positions WHERE '
                    'user_id=? AND device_id=? AND track_key=?',
                    (user_id, device_id, key),
                ).fetchone()
            if state == 'stopped' and pos <= 0 and previous is not None:
                pos = float(previous['position'])
            duration = max(
                0.0,
                float(track.get('duration') or 0),
                float(previous['duration']) if previous else 0.0,
            )
            previous_max = (
                float(previous['max_position'])
                if previous is not None
                else 0.0
            )
            if (
                not seek
                and state == 'playing'
                and previous is not None
                and previous['state'] == 'playing'
            ):
                pos = max(pos, float(previous['position']))
            replay = bool(
                previous is not None
                and state == 'playing'
                and pos <= 1
                and (
                    seek
                    or previous['state'] == 'stopped'
                    or previous['completed_at']
                )
            )
            started = previous is None or replay
            started_at = (
                now if started or previous is None else previous['started_at']
            )
            completed_at = (
                None
                if started or previous is None
                else previous['completed_at']
            )
            max_position = max(previous_max, pos)
            completed = False
            if state == 'playing' and duration > 0 and pos >= duration * 0.9:
                completed = not self._has_event(
                    conn, user_id, device_id, key, 'complete', started_at
                )
                if completed:
                    completed_at = now
            skipped_row = None
            if (
                current is not None
                and current['track_key'] != key
                and current['state'] == 'playing'
            ):
                skipped_row = current
            elif (
                state == 'stopped'
                and previous is not None
                and previous['state'] == 'playing'
            ):
                skipped_row = previous
            skipped = False
            if skipped_row is not None and self._should_skip(skipped_row, now):
                skipped = not self._has_event(
                    conn,
                    user_id,
                    device_id,
                    skipped_row['track_key'],
                    'skip',
                    skipped_row['started_at'],
                )
            seconds = 0.0
            if (
                previous is not None
                and previous['state'] == 'playing'
                and state == 'playing'
                and not seek
            ):
                delta = pos - previous_max
                if 0 < delta <= 45:
                    seconds = delta
            if key:
                conn.execute(
                    'INSERT INTO playback_positions '
                    '(user_id, device_id, player, track_key, track_json, '
                    'position, max_position, duration, state, started_at, '
                    'completed_at, updated_at) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) '
                    'ON CONFLICT(user_id, device_id, track_key) DO UPDATE SET '
                    'player=excluded.player, track_json=excluded.track_json, '
                    'position=excluded.position, '
                    'max_position=excluded.max_position, '
                    'duration=excluded.duration, state=excluded.state, '
                    'started_at=excluded.started_at, '
                    'completed_at=excluded.completed_at, '
                    'updated_at=excluded.updated_at',
                    (
                        user_id,
                        device_id,
                        player,
                        key,
                        json.dumps(track),
                        pos,
                        max_position,
                        duration,
                        state,
                        started_at,
                        completed_at,
                        now,
                    ),
                )
            conn.execute(
                'INSERT INTO playback_daily '
                '(user_id, day, seconds, plays, completions, skips) '
                'VALUES (?, ?, ?, ?, ?, ?) '
                'ON CONFLICT(user_id, day) DO UPDATE SET '
                'seconds=playback_daily.seconds+excluded.seconds, '
                'plays=playback_daily.plays+excluded.plays, '
                'completions=playback_daily.completions+excluded.completions, '
                'skips=playback_daily.skips+excluded.skips',
                (
                    user_id,
                    day,
                    seconds,
                    int(started),
                    int(completed),
                    int(skipped),
                ),
            )
            if skipped and skipped_row is not None:
                self._insert_event(
                    conn,
                    user_id,
                    device_id,
                    player,
                    skipped_row,
                    'skip',
                    now,
                )
            event_row = {
                'track_key': key,
                'track_json': json.dumps(track),
                'position': pos,
                'duration': duration,
            }
            if completed:
                self._insert_event(
                    conn,
                    user_id,
                    device_id,
                    player,
                    event_row,
                    'complete',
                    now,
                    seconds=seconds,
                )
            elif started:
                self._insert_event(
                    conn,
                    user_id,
                    device_id,
                    player,
                    event_row,
                    'start',
                    now,
                    seconds=seconds,
                )
            elif seconds:
                self._insert_event(
                    conn,
                    user_id,
                    device_id,
                    player,
                    event_row,
                    'heartbeat',
                    now,
                    seconds=seconds,
                )
        return {
            'track': track,
            'position': pos,
            'duration': duration,
            'device_id': device_id,
            'player': player,
            'updated_at': now,
        }

    @staticmethod
    def _has_event(
        conn: sqlite3.Connection,
        user_id: int,
        device_id: str,
        track_key: str,
        kind: str,
        since: str,
    ) -> bool:
        return (
            conn.execute(
                'SELECT 1 FROM playback_events WHERE '
                'user_id=? AND device_id=? AND track_key=? AND kind=? '
                'AND at>=? LIMIT 1',
                (user_id, device_id, track_key, kind, since),
            ).fetchone()
            is not None
        )

    @staticmethod
    def _should_skip(row: sqlite3.Row, now: str) -> bool:
        duration = float(row['duration'])
        position = float(row['position'])
        elapsed = (
            datetime.fromisoformat(now)
            - datetime.fromisoformat(row['started_at'])
        ).total_seconds()
        return duration <= 0 or position < duration * 0.25 or elapsed < 15

    @staticmethod
    def _insert_event(
        conn: sqlite3.Connection,
        user_id: int,
        device_id: str,
        player: str,
        row: dict[str, Any] | sqlite3.Row,
        kind: str,
        at: str,
        *,
        seconds: float = 0.0,
    ) -> None:
        conn.execute(
            'INSERT INTO playback_events '
            '(user_id, device_id, player, track_key, track_json, kind, '
            'position, duration, seconds, at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                user_id,
                device_id,
                player,
                row['track_key'],
                row['track_json'],
                kind,
                float(row['position']),
                float(row['duration']),
                seconds,
                at,
            ),
        )

    def summary(self, user_id: int, days: int = 30) -> dict[str, Any]:
        window = max(1, int(days or 30))
        cutoff = (
            (datetime.now(timezone.utc) - timedelta(days=window - 1))
            .date()
            .isoformat()
        )
        with self._connect() as conn:
            if user_id:
                where = 'WHERE user_id=? AND day>=?'
                args = (user_id, cutoff)
            else:
                where = 'WHERE day>=?'
                args = (cutoff,)
            row = conn.execute(
                'SELECT COALESCE(SUM(seconds), 0) AS seconds, '
                'COALESCE(SUM(plays), 0) AS plays, '
                'COALESCE(SUM(completions), 0) AS completions, '
                'COALESCE(SUM(skips), 0) AS skips '
                f'FROM playback_daily {where}',
                args,
            ).fetchone()
        plays = int(row['plays'])
        return {
            'seconds': int(round(float(row['seconds']))),
            'plays': plays,
            'completions': int(row['completions']),
            'skips': int(row['skips']),
            'completion_rate': (
                round(int(row['completions']) / plays, 4) if plays else 0.0
            ),
            'skip_rate': round(int(row['skips']) / plays, 4) if plays else 0.0,
        }

    def positions(self, user_id: int, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT * FROM playback_positions WHERE user_id=? '
                'ORDER BY updated_at DESC LIMIT ?',
                (user_id, max(1, int(limit))),
            ).fetchall()
        return [self._position(row) for row in rows]

    def forget_user(self, user_id: int) -> int:
        with self._connect() as conn:
            return sum(
                conn.execute(
                    f'DELETE FROM {table} WHERE user_id=?', (user_id,)
                ).rowcount
                for table in (
                    'playback_positions',
                    'playback_events',
                    'playback_daily',
                )
            )

    def prune(self, days: int = 365) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))
        stamp = cutoff.isoformat()
        day = cutoff.date().isoformat()
        with self._connect() as conn:
            return sum(
                conn.execute(
                    f'DELETE FROM {table} WHERE {column} < ?',
                    (day if column == 'day' else stamp,),
                ).rowcount
                for table, column in (
                    ('playback_positions', 'updated_at'),
                    ('playback_events', 'at'),
                    ('playback_daily', 'day'),
                )
            )

    def latest(self, user_id: int) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT * FROM playback_positions WHERE user_id=? '
                'ORDER BY updated_at DESC LIMIT 1',
                (user_id,),
            ).fetchone()
        return self._position(row) if row else None

    @staticmethod
    def _position(row: sqlite3.Row) -> dict[str, Any]:
        return {
            'track': json.loads(row['track_json']),
            'position': float(row['position']),
            'duration': float(row['duration']),
            'device_id': row['device_id'],
            'player': row['player'],
            'state': row['state'],
            'updated_at': row['updated_at'],
        }
