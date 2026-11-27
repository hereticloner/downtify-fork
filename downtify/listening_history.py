"""Canonical, cross-provider listening history for Stats."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from . import lastfm_history, spotify_history
from .sqlite_utils import connect_sqlite

_SOURCE_PRIORITY = {'downtify': 0, 'spotify': 1, 'lastfm': 2}
_MAX_MATCH_SECONDS = 1800
DAY_PLAYS_LIMIT = 400


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
        played_at = played_at if played_at.endswith('Z') else when.isoformat()
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
        self, user_id: int = 0, recent_limit: int = 400, *, days: int = 30
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
        window = days if days in {7, 30, 90} else 30
        today = datetime.now(timezone.utc).date()
        window_start = (today - timedelta(days=window - 1)).isoformat()
        window_end = today.isoformat()
        period_where = f'{where} AND ' if where else 'WHERE '
        period_args: tuple[Any, ...] = (*args, window_start, window_end)
        loved_plays = 0
        mbid_plays = 0
        imported_plays = 0
        with self._connect() as conn:
            total = int(
                conn.execute(
                    f'SELECT COUNT(*) FROM listening_events {where}', args
                ).fetchone()[0]
            )
            top_tracks = [
                {
                    'summary': row['summary'],
                    'artist': row['artist'],
                    'title': row['title'],
                    'album': row['album'],
                    'count': int(row['count']),
                }
                for row in conn.execute(
                    f'SELECT {summary_sql} AS summary, MAX(artist) AS artist, '
                    'MAX(title) AS title, MAX(album) AS album, '
                    'COUNT(*) AS count '
                    f'FROM listening_events {where} '
                    "GROUP BY summary HAVING summary != '' "
                    'ORDER BY count DESC, summary LIMIT 10',
                    args,
                ).fetchall()
            ]
            top_artists = [
                {'artist': row['artist'], 'count': int(row['count'])}
                for row in conn.execute(
                    'SELECT artist, COUNT(*) AS count '
                    f'FROM listening_events {where}'
                    + (" AND artist != ''" if where else " WHERE artist != ''")
                    + ' GROUP BY artist ORDER BY count DESC, artist LIMIT 10',
                    args,
                ).fetchall()
            ]
            top_albums = [
                {
                    'album': row['album'],
                    'artist': row['artist'],
                    'count': int(row['count']),
                }
                for row in conn.execute(
                    'SELECT album, artist, COUNT(*) AS count '
                    f'FROM listening_events {where}'
                    + (" AND album != ''" if where else " WHERE album != ''")
                    + ' GROUP BY album, artist ORDER BY count DESC, album, artist '
                    'LIMIT 8',
                    args,
                ).fetchall()
            ]
            profile_unique = conn.execute(
                'SELECT '
                "COUNT(DISTINCT CASE WHEN match_key != '|' THEN match_key END) "
                "AS tracks, COUNT(DISTINCT NULLIF(artist, '')) AS artists, "
                "COUNT(DISTINCT NULLIF(album, '')) AS albums "
                f'FROM listening_events {where}',
                args,
            ).fetchone()
            profile_sources = {source: 0 for source in _SOURCE_PRIORITY}
            for row in conn.execute(
                'SELECT source, COUNT(*) AS count '
                f'FROM listening_events {where} GROUP BY source',
                args,
            ):
                if row['source'] in profile_sources:
                    profile_sources[row['source']] = int(row['count'])
            profile_range = conn.execute(
                'SELECT MIN(played_at) AS first_at, MAX(played_at) AS last_at '
                f'FROM listening_events {where}',
                args,
            ).fetchone()
            daily_where = f'{where} AND ' if where else 'WHERE '
            daily = [
                {'date': row['day'], 'count': int(row['count'])}
                for row in conn.execute(
                    'SELECT date(played_at) AS day, COUNT(*) AS count '
                    f'FROM listening_events {daily_where}'
                    'date(played_at)>=? GROUP BY day ORDER BY day',
                    (*args, cutoff),
                ).fetchall()
            ]
            recent = [
                {
                    'at': row['played_at'],
                    'date': row['day'],
                    'summary': row['summary'],
                    'artist': row['artist'],
                    'title': row['title'],
                    'album': row['album'],
                    'context': row['context'],
                    'context_type': row['context_type'],
                    'source': row['source'],
                }
                for row in conn.execute(
                    f'SELECT played_at, date(played_at) AS day, '
                    f'{summary_sql} AS summary, artist, title, album, context, '
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
            by_source = {source: 0 for source in _SOURCE_PRIORITY}
            for row in conn.execute(
                'SELECT source, COUNT(*) AS count '
                f'FROM listening_events {period_where}'
                'date(played_at) BETWEEN ? AND ? GROUP BY source',
                period_args,
            ):
                if row['source'] in by_source:
                    by_source[row['source']] = int(row['count'])
            unique = conn.execute(
                'SELECT '
                "COUNT(DISTINCT CASE WHEN match_key != '|' THEN match_key END) "
                "AS tracks, COUNT(DISTINCT NULLIF(artist, '')) AS artists, "
                "COUNT(DISTINCT NULLIF(album, '')) AS albums "
                f'FROM listening_events {period_where}'
                'date(played_at) BETWEEN ? AND ?',
                period_args,
            ).fetchone()
            duration = conn.execute(
                'SELECT COALESCE(SUM(CASE WHEN duration_ms > 0 '
                'THEN duration_ms ELSE 0 END), 0) AS duration_ms, '
                'COALESCE(SUM(CASE WHEN duration_ms > 0 THEN 1 ELSE 0 END), 0) '
                'AS with_duration '
                f'FROM listening_events {period_where}'
                'date(played_at) BETWEEN ? AND ?',
                period_args,
            ).fetchone()
            by_hour = [0] * 24
            by_weekday = [0] * 7
            for row in conn.execute(
                "SELECT CAST(strftime('%H', played_at) AS INTEGER) AS hour, "
                'COUNT(*) AS count '
                f'FROM listening_events {period_where}'
                'date(played_at) BETWEEN ? AND ? GROUP BY hour',
                period_args,
            ):
                if row['hour'] is not None and 0 <= int(row['hour']) < 24:
                    by_hour[int(row['hour'])] = int(row['count'])
            for row in conn.execute(
                "SELECT CAST(strftime('%w', played_at) AS INTEGER) AS weekday, "
                'COUNT(*) AS count '
                f'FROM listening_events {period_where}'
                'date(played_at) BETWEEN ? AND ? GROUP BY weekday',
                period_args,
            ):
                if row['weekday'] is not None and 0 <= int(row['weekday']) < 7:
                    by_weekday[int(row['weekday'])] = int(row['count'])
            has_lastfm = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (lastfm_history.TABLE,),
            ).fetchone()
            if has_lastfm:
                event_where = 'WHERE e.user_id=?' if user_id else ''
                loved_sql = (
                    'CASE WHEN json_valid(l.raw_json) THEN '
                    "CAST(json_extract(l.raw_json, '$.loved') AS INTEGER) "
                    'ELSE 0 END'
                )
                detail = conn.execute(
                    'SELECT COUNT(DISTINCT CASE WHEN '
                    f'{loved_sql} = 1 THEN e.id END) AS loved, '
                    "COUNT(DISTINCT CASE WHEN l.mbid != '' THEN e.id END) AS mbid "
                    f'FROM listening_events e JOIN {lastfm_history.TABLE} l '
                    'ON l.listening_event_id=e.id '
                    f'{event_where} '
                    'AND date(e.played_at) BETWEEN ? AND ?',
                    period_args,
                ).fetchone()
                loved_plays = int(detail['loved'])
                mbid_plays = int(detail['mbid'])
                imported_plays = int(
                    conn.execute(
                        f'SELECT COUNT(*) FROM {lastfm_history.TABLE}'
                    ).fetchone()[0]
                )
        period_total = sum(by_source.values())
        with_duration = int(duration['with_duration'])
        daily_counts = {row['date']: row['count'] for row in daily}
        weeks = []
        for index in range(4):
            end = today - timedelta(days=(3 - index) * 7)
            start = end - timedelta(days=6)
            weeks.append({
                'start': start.isoformat(),
                'end': end.isoformat(),
                'count': sum(
                    daily_counts.get(
                        (start + timedelta(days=offset)).isoformat(), 0
                    )
                    for offset in range(7)
                ),
            })
        state = lastfm_history.import_state(self._path)
        lastfm = {
            'loved_plays': loved_plays,
            'mbid_plays': mbid_plays,
            'imported_plays': imported_plays,
            'backfill': {
                'done': bool(state['backfill_done']),
                'oldest_at': state['oldest_at'],
                'newest_at': state['newest_at'],
            },
        }
        return {
            'total': total,
            'top_tracks': top_tracks,
            'daily': daily,
            'recent': recent,
            'top_contexts': contexts,
            'profile': {
                'first_at': profile_range['first_at'] or '',
                'last_at': profile_range['last_at'] or '',
                'unique': {
                    'tracks': int(profile_unique['tracks']),
                    'artists': int(profile_unique['artists']),
                    'albums': int(profile_unique['albums']),
                },
                'by_source': profile_sources,
                'top_artists': top_artists,
                'top_albums': top_albums,
                'weeks': weeks,
            },
            'period': {
                'days': window,
                'total': period_total,
                'by_source': by_source,
            },
            'unique': {
                'tracks': int(unique['tracks']),
                'artists': int(unique['artists']),
                'albums': int(unique['albums']),
            },
            'track_time': {
                'seconds': int(duration['duration_ms']) // 1000,
                'plays_with_duration': with_duration,
                'plays_without_duration': period_total - with_duration,
            },
            'patterns': {'by_hour': by_hour, 'by_weekday': by_weekday},
            'lastfm': lastfm,
        }

    def pattern_detail(
        self,
        user_id: int,
        days: int,
        kind: str,
        bucket: int,
        *,
        top_limit: int = 5,
        recent_limit: int = 50,
    ) -> dict[str, Any]:
        """Exact canonical plays for one UTC hour or weekday bucket."""

        if kind not in {'hour', 'weekday'}:
            raise ValueError('kind must be hour or weekday')
        try:
            selected = int(bucket)
        except (TypeError, ValueError) as exc:
            raise ValueError('bucket must be an integer') from exc
        maximum = 23 if kind == 'hour' else 6
        if selected < 0 or selected > maximum:
            raise ValueError('bucket is out of range')
        window = days if days in {7, 30, 90} else 30
        today = datetime.now(timezone.utc).date()
        start = (today - timedelta(days=window - 1)).isoformat()
        where = 'WHERE user_id=?' if user_id else ''
        args: list[Any] = [int(user_id)] if user_id else []
        period_where = f'{where} AND ' if where else 'WHERE '
        bucket_sql = (
            "CAST(strftime('%H', played_at) AS INTEGER)"
            if kind == 'hour'
            else "CAST(strftime('%w', played_at) AS INTEGER)"
        )
        bucket_args: tuple[Any, ...] = (
            *args,
            start,
            today.isoformat(),
            selected,
        )
        summary_sql = (
            "CASE WHEN artist != '' AND title != '' "
            "THEN artist || ' - ' || title "
            "WHEN title != '' THEN title ELSE artist END"
        )
        with self._connect() as conn:
            total = int(
                conn.execute(
                    'SELECT COUNT(*) FROM listening_events '
                    f'{period_where}date(played_at) BETWEEN ? AND ? '
                    f'AND {bucket_sql}=?',
                    bucket_args,
                ).fetchone()[0]
            )
            by_source = {source: 0 for source in _SOURCE_PRIORITY}
            for row in conn.execute(
                'SELECT source, COUNT(*) AS count FROM listening_events '
                f'{period_where}date(played_at) BETWEEN ? AND ? '
                f'AND {bucket_sql}=? GROUP BY source',
                bucket_args,
            ):
                if row['source'] in by_source:
                    by_source[row['source']] = int(row['count'])
            top_tracks = [
                {'summary': row['summary'], 'count': int(row['count'])}
                for row in conn.execute(
                    f'SELECT {summary_sql} AS summary, COUNT(*) AS count '
                    'FROM listening_events '
                    f'{period_where}date(played_at) BETWEEN ? AND ? '
                    f"AND {bucket_sql}=? GROUP BY summary HAVING summary != '' "
                    'ORDER BY count DESC, summary LIMIT ?',
                    (*bucket_args, max(1, min(int(top_limit), 20))),
                ).fetchall()
            ]
            top_artists = [
                {'artist': row['artist'], 'count': int(row['count'])}
                for row in conn.execute(
                    'SELECT artist, COUNT(*) AS count FROM listening_events '
                    f'{period_where}date(played_at) BETWEEN ? AND ? '
                    f"AND {bucket_sql}=? AND artist != '' "
                    'GROUP BY artist ORDER BY count DESC, artist LIMIT ?',
                    (*bucket_args, max(1, min(int(top_limit), 20))),
                ).fetchall()
            ]
            recent = [
                {
                    'at': row['played_at'],
                    'date': row['day'],
                    'summary': row['summary'],
                    'context': row['context'],
                    'context_type': row['context_type'],
                    'source': row['source'],
                }
                for row in conn.execute(
                    f'SELECT played_at, date(played_at) AS day, '
                    f'{summary_sql} AS summary, context, context_type, source '
                    'FROM listening_events '
                    f'{period_where}date(played_at) BETWEEN ? AND ? '
                    f'AND {bucket_sql}=? ORDER BY played_at DESC, id DESC LIMIT ?',
                    (*bucket_args, max(1, min(int(recent_limit), 200))),
                ).fetchall()
            ]
        return {
            'kind': kind,
            'bucket': selected,
            'total': total,
            'by_source': by_source,
            'top_tracks': top_tracks,
            'top_artists': top_artists,
            'recent': recent,
            'truncated': total > len(recent),
        }

    def day_plays(
        self,
        on_date: str,
        user_id: int = 0,
        limit: int = DAY_PLAYS_LIMIT,
    ) -> dict[str, Any]:
        """One exact UTC day, with its true total and a bounded play page."""

        empty = {'date': str(on_date or ''), 'total': 0, 'plays': []}
        if not on_date:
            return empty
        where = 'WHERE user_id=?' if user_id else ''
        args: list[Any] = [int(user_id)] if user_id else []
        summary_sql = (
            "CASE WHEN artist != '' AND title != '' "
            "THEN artist || ' - ' || title "
            "WHEN title != '' THEN title ELSE artist END"
        )
        with self._connect() as conn:
            day_where = f'{where} AND ' if where else 'WHERE '
            day_args: tuple[Any, ...] = (*args, str(on_date))
            total = int(
                conn.execute(
                    'SELECT COUNT(*) FROM listening_events '
                    f'{day_where}date(played_at)=?',
                    day_args,
                ).fetchone()[0]
            )
            plays = [
                {
                    'at': row['played_at'],
                    'date': row['day'],
                    'summary': row['summary'],
                    'context': row['context'],
                    'context_type': row['context_type'],
                    'source': row['source'],
                }
                for row in conn.execute(
                    f'SELECT played_at, date(played_at) AS day, {summary_sql} AS summary, context, '
                    f'context_type, source FROM listening_events {day_where}'
                    'date(played_at)=? '
                    'ORDER BY played_at DESC, id DESC LIMIT ?',
                    (*day_args, max(1, min(int(limit), DAY_PLAYS_LIMIT))),
                ).fetchall()
            ]
        return {'date': str(on_date), 'total': total, 'plays': plays}

    @staticmethod
    def _fill_spotify_event(conn: sqlite3.Connection, row: Any) -> int:
        try:
            context = json.loads(row['context_json'] or '{}')
        except (TypeError, ValueError):
            context = {}
        if not isinstance(context, dict):
            context = {}
        event_id = int(row['listening_event_id'])
        event = conn.execute(
            'SELECT album, context, context_type FROM listening_events WHERE id=?',
            (event_id,),
        ).fetchone()
        if event is None:
            return 0
        raw_values = {
            'album': str(row['album_name'] or '').strip(),
            'context': str(
                context.get('uri') or context.get('href') or ''
            ).strip(),
            'context_type': str(context.get('type') or '').strip(),
        }
        assignments: list[str] = []
        conditions: list[str] = []
        values: list[Any] = []
        for column, value in raw_values.items():
            if value and not str(event[column] or '').strip():
                assignments.append(f'{column}=?')
                conditions.append(f"{column}=''")
                values.append(value)
        if not assignments:
            return 0
        cursor = conn.execute(
            'UPDATE listening_events SET '
            + ', '.join(assignments)
            + ' WHERE id=? AND '
            + ' AND '.join(conditions),
            (*values, event_id),
        )
        return max(0, int(cursor.rowcount))

    def _enrich_spotify_rows(self, conn: sqlite3.Connection, size: int) -> int:
        updated = 0
        last_id = 0
        while True:
            rows = conn.execute(
                f'SELECT id, listening_event_id, album_name, context_json '
                f'FROM {spotify_history.TABLE} '
                'WHERE id>? AND listening_event_id IS NOT NULL '
                "AND (album_name != '' OR context_json NOT IN ('', '{}')) "
                'ORDER BY id LIMIT ?',
                (last_id, size),
            ).fetchall()
            if not rows:
                return updated
            for row in rows:
                updated += self._fill_spotify_event(conn, row)
            last_id = int(rows[-1]['id'])

    @staticmethod
    def _enrich_lastfm_rows(conn: sqlite3.Connection, size: int) -> int:
        updated = 0
        last_id = 0
        while True:
            rows = conn.execute(
                f'SELECT id, listening_event_id, album_name '
                f'FROM {lastfm_history.TABLE} WHERE id>? '
                'AND listening_event_id IS NOT NULL '
                "AND album_name != '' ORDER BY id LIMIT ?",
                (last_id, size),
            ).fetchall()
            if not rows:
                return updated
            for row in rows:
                cursor = conn.execute(
                    'UPDATE listening_events SET album=? '
                    "WHERE id=? AND album=''",
                    (
                        str(row['album_name'] or '').strip(),
                        int(row['listening_event_id']),
                    ),
                )
                updated += max(0, int(cursor.rowcount))
            last_id = int(rows[-1]['id'])

    def enrich_from_raw(self, batch_size: int = 500) -> int:
        """Fill blank canonical metadata from linked raw provider rows."""

        size = max(1, min(int(batch_size), 5000))
        try:
            with self._connect() as conn:
                tables = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
                if spotify_history.TABLE in tables:
                    return self._enrich_spotify_rows(conn, size) + (
                        self._enrich_lastfm_rows(conn, size)
                        if lastfm_history.TABLE in tables
                        else 0
                    )
                if lastfm_history.TABLE in tables:
                    return self._enrich_lastfm_rows(conn, size)
        except sqlite3.Error:
            return 0
        return 0

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


async def bootstrap_listening_history(
    activity: Any,
    db_path: Any,
    listening: Any,
    *,
    user_id: int,
    batch_size: int = 200,
    pause: float = 0.05,
) -> int:
    """Drain provider backlogs without holding up application startup."""

    linked = 0
    for module in (spotify_history, lastfm_history):
        while True:
            count = await asyncio.to_thread(
                module.link_pending,
                db_path,
                listening,
                user_id=user_id,
                limit=batch_size,
            )
            linked += count
            if not count:
                break
            await asyncio.sleep(pause)
    await asyncio.to_thread(listening.backfill_activity, activity)
    await asyncio.to_thread(listening.enrich_from_raw)
    return linked
