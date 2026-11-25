"""Canonical, cross-provider listening history for Stats."""

from __future__ import annotations

import sqlite3
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .sqlite_utils import connect_sqlite

_SOURCE_PRIORITY = {'downtify': 0, 'spotify': 1, 'lastfm': 2}
_MAX_MATCH_SECONDS = 1800


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def source_priority(source: str) -> int:
    return _SOURCE_PRIORITY[source]


def normalize_match_key(artist: str, title: str) -> str:
    def clean(value: str) -> str:
        return ' '.join(
            unicodedata.normalize('NFKC', value).casefold().split()
        )

    return f'{clean(artist)}|{clean(title)}'


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class ListeningStore:
    """One canonical play per real listen, with raw sources linked separately."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS listening_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    identity_key TEXT NOT NULL,
                    source_key TEXT NOT NULL,
                    played_at TEXT NOT NULL,
                    match_key TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    artist TEXT NOT NULL DEFAULT '',
                    album TEXT NOT NULL DEFAULT '',
                    spotify_track_id TEXT NOT NULL DEFAULT '',
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    context TEXT NOT NULL DEFAULT '',
                    context_type TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    UNIQUE (user_id, identity_key)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS listening_event_sources (
                    event_id INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    source_key TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (event_id, source)
                )
            """)
            columns = {
                row[1]
                for row in conn.execute(
                    'PRAGMA table_info(listening_event_sources)'
                )
            }
            if 'source_key' not in columns:
                conn.execute(
                    'ALTER TABLE listening_event_sources ADD COLUMN '
                    "source_key TEXT NOT NULL DEFAULT ''"
                )
            conn.execute(
                'CREATE INDEX IF NOT EXISTS listening_source_identity '
                'ON listening_event_sources (source, source_key)'
            )
            conn.execute(
                'CREATE INDEX IF NOT EXISTS listening_match '
                'ON listening_events (user_id, match_key, played_at)'
            )
            conn.execute(
                'CREATE INDEX IF NOT EXISTS listening_recent '
                'ON listening_events (user_id, played_at DESC)'
            )

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._path, row_factory=True)

    def link_or_create(
        self,
        *,
        user_id: int,
        source: str,
        source_key: str,
        played_at: str,
        title: str,
        artist: str,
        album: str = '',
        spotify_track_id: str = '',
        duration_ms: int = 0,
        context: str = '',
        context_type: str = '',
    ) -> tuple[int, bool]:
        if source not in _SOURCE_PRIORITY:
            raise ValueError(f'unknown listening source: {source}')
        identity_key = f'{source}:{source_key}'
        match_key = normalize_match_key(artist, title)
        when = _parse_time(played_at)
        duration = max(0, int(duration_ms or 0))
        with self._connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            existing = conn.execute(
                'SELECT s.event_id FROM listening_event_sources s '
                'JOIN listening_events e ON e.id=s.event_id '
                'WHERE e.user_id=? AND s.source=? AND s.source_key=?',
                (int(user_id), source, source_key),
            ).fetchone()
            if existing is None:
                existing = conn.execute(
                    'SELECT id FROM listening_events '
                    'WHERE user_id=? AND identity_key=?',
                    (int(user_id), identity_key),
                ).fetchone()
            if existing is not None:
                if 'event_id' in existing.keys():
                    event_id = int(existing['event_id'])
                else:
                    event_id = int(existing['id'])
                    conn.execute(
                        'UPDATE listening_event_sources SET source_key=? '
                        'WHERE event_id=? AND source=?',
                        (source_key, event_id, source),
                    )
                return event_id, False
            candidates = conn.execute(
                'SELECT * FROM listening_events '
                'WHERE user_id=? AND match_key=? '
                'AND julianday(played_at) BETWEEN julianday(?) - ? '
                'AND julianday(?) + ? '
                'ORDER BY ABS(julianday(played_at) - julianday(?))',
                (
                    int(user_id),
                    match_key,
                    played_at,
                    _MAX_MATCH_SECONDS / 86400,
                    played_at,
                    _MAX_MATCH_SECONDS / 86400,
                    played_at,
                ),
            ).fetchall()
            for candidate in candidates:
                linked = conn.execute(
                    'SELECT 1 FROM listening_event_sources '
                    'WHERE event_id=? AND source=?',
                    (candidate['id'], source),
                ).fetchone()
                if linked is not None:
                    continue
                delta = abs(
                    (
                        _parse_time(candidate['played_at']) - when
                    ).total_seconds()
                )
                window = max(
                    300,
                    min(
                        max(duration, int(candidate['duration_ms'])) / 1000
                        + 300,
                        _MAX_MATCH_SECONDS,
                    ),
                )
                if delta > window:
                    continue
                if source_priority(source) < source_priority(
                    candidate['source']
                ):
                    conn.execute(
                        'UPDATE listening_events SET source=?, source_key=?, '
                        'played_at=?, match_key=?, title=?, artist=?, album=?, '
                        'spotify_track_id=?, duration_ms=?, context=?, '
                        'context_type=? WHERE id=?',
                        (
                            source,
                            source_key,
                            played_at,
                            match_key,
                            title,
                            artist,
                            album,
                            spotify_track_id,
                            duration,
                            context,
                            context_type,
                            candidate['id'],
                        ),
                    )
                conn.execute(
                    'INSERT INTO listening_event_sources '
                    '(event_id, source, source_key) VALUES (?, ?, ?)',
                    (candidate['id'], source, source_key),
                )
                return int(candidate['id']), False
            cursor = conn.execute(
                'INSERT INTO listening_events '
                '(user_id, source, identity_key, source_key, played_at, '
                'match_key, title, artist, album, spotify_track_id, '
                'duration_ms, context, context_type, created_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    int(user_id),
                    source,
                    identity_key,
                    source_key,
                    played_at,
                    match_key,
                    title,
                    artist,
                    album,
                    spotify_track_id,
                    duration,
                    context,
                    context_type,
                    _now(),
                ),
            )
            event_id = int(cursor.lastrowid)
            conn.execute(
                'INSERT INTO listening_event_sources '
                '(event_id, source, source_key) VALUES (?, ?, ?)',
                (event_id, source, source_key),
            )
        return event_id, True

    def backfill_activity(self, activity: Any) -> int:
        created = 0
        before = 0
        while True:
            page = activity.entries(
                kinds=['playback'], limit=100, before=before, user_id=0
            )
            for entry in page['entries']:
                detail = entry.get('detail')
                track = (
                    detail.get('track') if isinstance(detail, dict) else None
                )
                if not isinstance(track, dict):
                    track = {}
                try:
                    duration_ms = int(float(track.get('duration') or 0) * 1000)
                except (TypeError, ValueError):
                    duration_ms = 0
                summary = str(entry.get('summary') or '').strip()
                _event_id, landed = self.link_or_create(
                    user_id=int(entry.get('user_id') or 0),
                    source='downtify',
                    source_key=f'activity:{entry["id"]}',
                    played_at=str(entry.get('at') or ''),
                    title=str(track.get('title') or summary).strip(),
                    artist=str(track.get('artist') or '').strip(),
                    album=str(track.get('album') or '').strip(),
                    spotify_track_id=str(track.get('track_id') or '').strip(),
                    duration_ms=duration_ms,
                    context=str(track.get('context') or '').strip(),
                    context_type=str(track.get('context_type') or '').strip(),
                )
                created += int(landed)
            nxt = int(page.get('next') or 0)
            if not nxt or not page['entries']:
                break
            before = nxt
        return created

    def stats(
        self, user_id: int = 0, recent_limit: int = 400
    ) -> dict[str, Any]:
        where = 'WHERE user_id=?' if user_id else ''
        args: list[Any] = [int(user_id)] if user_id else []
        summary_sql = (
            "CASE WHEN artist != '' AND title != '' "
            "THEN artist || ' - ' || title "
            "WHEN title != '' THEN title ELSE artist END"
        )
        cutoff = (
            datetime.now(timezone.utc).date() - timedelta(days=363)
        ).isoformat()
        with self._connect() as conn:
            total = int(
                conn.execute(
                    f'SELECT COUNT(*) FROM listening_events {where}', args
                ).fetchone()[0]
            )
            top_tracks = [
                {'summary': row['summary'], 'count': int(row['count'])}
                for row in conn.execute(
                    f'SELECT {summary_sql} AS summary, COUNT(*) AS count '
                    f'FROM listening_events {where} '
                    "GROUP BY summary HAVING summary != '' "
                    'ORDER BY count DESC, summary LIMIT 10',
                    args,
                ).fetchall()
            ]
            daily_where = f'{where} AND ' if where else 'WHERE '
            daily = [
                {'date': row['day'], 'count': int(row['count'])}
                for row in conn.execute(
                    'SELECT substr(played_at, 1, 10) AS day, COUNT(*) AS count '
                    f'FROM listening_events {daily_where}'
                    'substr(played_at, 1, 10)>=? GROUP BY day ORDER BY day',
                    (*args, cutoff),
                ).fetchall()
            ]
            recent = [
                {
                    'at': row['played_at'],
                    'date': str(row['played_at'])[:10],
                    'summary': row['summary'],
                    'context': row['context'],
                    'context_type': row['context_type'],
                    'source': row['source'],
                }
                for row in conn.execute(
                    f'SELECT played_at, {summary_sql} AS summary, context, '
                    f'context_type, source FROM listening_events {where} '
                    'ORDER BY played_at DESC, id DESC LIMIT ?',
                    (*args, max(1, int(recent_limit))),
                ).fetchall()
            ]
            contexts = [
                {'context': row['context'], 'count': int(row['count'])}
                for row in conn.execute(
                    'SELECT context, COUNT(*) AS count '
                    f'FROM listening_events {where}'
                    + (
                        " AND context != ''"
                        if where
                        else " WHERE context != ''"
                    )
                    + ' GROUP BY context ORDER BY count DESC, context LIMIT 10',
                    args,
                ).fetchall()
            ]
        return {
            'total': total,
            'top_tracks': top_tracks,
            'daily': daily,
            'recent': recent,
            'top_contexts': contexts,
        }

    def forget_user(self, user_id: int) -> int:
        with self._connect() as conn:
            before = conn.total_changes
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            for table in ('spotify_recently_played', 'lastfm_recent_tracks'):
                if table in tables:
                    conn.execute(
                        f'DELETE FROM {table} WHERE user_id=?', (int(user_id),)
                    )
            conn.execute(
                'DELETE FROM listening_event_sources WHERE event_id IN '
                '(SELECT id FROM listening_events WHERE user_id=?)',
                (int(user_id),),
            )
            conn.execute(
                'DELETE FROM listening_events WHERE user_id=?', (int(user_id),)
            )
            return conn.total_changes - before
