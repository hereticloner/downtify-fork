"""Import Last.fm scrobbles into Downtify's listening history."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import httpx
from loguru import logger

from . import scrobbling
from .sqlite_utils import connect_sqlite

Request = Callable[..., Any]
MAX_LIMIT = 200
TABLE = 'lastfm_recent_tracks'

_CREATE_TABLE = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 0,
    source_key TEXT NOT NULL UNIQUE,
    played_at TEXT NOT NULL,
    uts INTEGER NOT NULL,
    artist_name TEXT NOT NULL DEFAULT '',
    track_name TEXT NOT NULL DEFAULT '',
    album_name TEXT NOT NULL DEFAULT '',
    mbid TEXT NOT NULL DEFAULT '',
    raw_json TEXT NOT NULL DEFAULT '{{}}',
    listening_event_id INTEGER,
    imported_at TEXT NOT NULL DEFAULT ''
)
"""


def _text(value: Any) -> str:
    return str(value or '').strip()


def _uts(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def import_enabled(settings: Any) -> bool:
    block = settings.get('scrobbling') if isinstance(settings, dict) else None
    return bool(
        isinstance(block, dict)
        and block.get('enabled')
        and block.get('lastfm_enabled')
        and block.get('import_history')
    )


def read_config(settings: Any) -> Optional[dict[str, str]]:
    if not import_enabled(settings):
        return None
    block = settings['scrobbling']
    api_key = _text(block.get('lastfm_api_key'))
    username = _text(block.get('lastfm_username'))
    if not api_key or not username:
        return None
    return {'api_key': api_key, 'username': username}


def _request(method: str, url: str, **kwargs: Any):
    return httpx.request(
        method, url, timeout=scrobbling.TIMEOUT_SECONDS, **kwargs
    )


def fetch_recent_tracks(
    config: dict[str, str],
    *,
    from_uts: Optional[int] = None,
    to_uts: Optional[int] = None,
    page: int = 1,
    limit: int = MAX_LIMIT,
    request: Optional[Request] = None,
) -> Optional[dict[str, Any]]:
    api_key = _text(config.get('api_key'))
    username = _text(config.get('username'))
    if not api_key or not username:
        return None
    params: dict[str, Any] = {
        'method': 'user.getRecentTracks',
        'user': username,
        'api_key': api_key,
        'format': 'json',
        'limit': max(1, min(int(limit), MAX_LIMIT)),
        'extended': 1,
    }
    if page > 1:
        params['page'] = page
    if from_uts is not None:
        params['from'] = int(from_uts)
    if to_uts is not None:
        params['to'] = int(to_uts)
    sender = request or _request
    try:
        response = sender('GET', scrobbling.LASTFM_API, params=params)
        response.raise_for_status()
        body = response.json()
    except Exception as exc:  # noqa: BLE001 - best-effort background import
        logger.warning('last.fm history fetch failed: {}', exc)
        return None
    if isinstance(body, dict):
        lfm = body.get('lfm')
        if isinstance(lfm, dict) and lfm.get('status') == 'failed':
            error = lfm.get('error')
            code = error.get('code') if isinstance(error, dict) else ''
            logger.warning('last.fm history API error: {}', code)
            return None
    return body if isinstance(body, dict) else None


def parse_plays(body: Any) -> list[dict[str, Any]]:
    recent = body.get('recenttracks') if isinstance(body, dict) else None
    tracks = recent.get('track') if isinstance(recent, dict) else None
    if isinstance(tracks, dict):
        tracks = [tracks]
    if not isinstance(tracks, list):
        return []
    rows: list[dict[str, Any]] = []
    for track in tracks:
        if not isinstance(track, dict):
            continue
        if str(track.get('nowplaying') or '').lower() == 'true':
            continue
        date = track.get('date')
        if not isinstance(date, dict):
            continue
        try:
            uts = int(date.get('uts') or 0)
        except (TypeError, ValueError):
            continue
        if uts <= 0:
            continue
        artist = track.get('artist')
        album = track.get('album')
        rows.append({
            'played_at': datetime.fromtimestamp(uts, timezone.utc).isoformat(),
            'uts': uts,
            'artist_name': _text(artist.get('name'))
            if isinstance(artist, dict)
            else '',
            'track_name': _text(track.get('name')),
            'album_name': _text(album.get('name'))
            if isinstance(album, dict)
            else '',
            'mbid': _text(track.get('mbid')),
            'raw_item': track,
        })
    return rows


def _connect(db_path: Any) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect_sqlite(str(path))
    conn.execute(_CREATE_TABLE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS history_import_state (
            source TEXT PRIMARY KEY,
            newest_at TEXT NOT NULL DEFAULT '',
            oldest_at TEXT NOT NULL DEFAULT '',
            backfill_done INTEGER NOT NULL DEFAULT 0
        )
    """)
    return conn


def ensure_schema(db_path: Any) -> None:
    """Create the raw Last.fm and import-state tables without importing."""

    _connect(db_path).close()


def _base_digest(row: dict[str, Any]) -> str:
    raw = '\0'.join((
        str(row.get('uts') or ''),
        _text(row.get('artist_name')).casefold(),
        _text(row.get('track_name')).casefold(),
        _text(row.get('mbid')).casefold(),
    ))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def save_recent_tracks(db_path: Any, rows: Any, *, user_id: int = 0) -> int:
    clean = [
        row
        for row in rows or []
        if isinstance(row, dict)
        and _uts(row.get('uts')) > 0
        and _text(row.get('played_at'))
    ]
    if not clean:
        return 0
    conn = _connect(db_path)
    try:
        before = conn.total_changes
        # shortcut: Last.fm has no scrobble id; identical same-second rows
        # use their position in the imported batch. Upgrade if one appears.
        counts: dict[str, int] = {}
        for row in clean:
            digest = _base_digest(row)
            prefix = f'lastfm:{digest}:'
            counts[digest] = counts.get(digest, 0) + 1
            raw = (
                row.get('raw_item')
                if isinstance(row.get('raw_item'), dict)
                else {}
            )
            conn.execute(
                f'INSERT OR IGNORE INTO {TABLE} '
                '(user_id, source_key, played_at, uts, artist_name, '
                'track_name, album_name, mbid, raw_json, listening_event_id, '
                'imported_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)',
                (
                    int(user_id or 0),
                    f'{prefix}{counts[digest]}',
                    _text(row.get('played_at')),
                    int(row.get('uts')),
                    _text(row.get('artist_name')),
                    _text(row.get('track_name')),
                    _text(row.get('album_name')),
                    _text(row.get('mbid')),
                    json.dumps(raw, ensure_ascii=False, separators=(',', ':')),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        conn.commit()
        return conn.total_changes - before
    except sqlite3.Error as exc:
        logger.warning('last.fm history store failed: {}', exc)
        return 0
    finally:
        conn.close()


def count_plays(db_path: Any) -> int:
    if not Path(db_path).is_file():
        return 0
    try:
        with connect_sqlite(str(db_path)) as conn:
            return int(
                conn.execute(f'SELECT COUNT(*) FROM {TABLE}').fetchone()[0]
            )
    except sqlite3.Error:
        return 0


def link_pending(
    db_path: Any, listening: Any, *, user_id: int = 0, limit: int = 500
) -> int:
    if listening is None or not Path(db_path).is_file():
        return 0
    try:
        conn = connect_sqlite(str(db_path), row_factory=True)
    except sqlite3.Error as exc:
        logger.warning('last.fm history link failed: {}', exc)
        return 0
    try:
        where = 'listening_event_id IS NULL'
        args: list[Any] = []
        if user_id:
            where += ' AND user_id=?'
            args.append(int(user_id))
        rows = conn.execute(
            f'SELECT * FROM {TABLE} WHERE {where} '
            'ORDER BY played_at, id LIMIT ?',
            (*args, max(1, min(int(limit), 5000))),
        ).fetchall()
    except sqlite3.Error:
        return 0
    finally:
        conn.close()
    linked: list[tuple[int, int]] = []
    for row in rows:
        event_id, _created = listening.link_or_create(
            user_id=int(row['user_id'] or user_id),
            source='lastfm',
            source_key=row['source_key'],
            played_at=row['played_at'],
            title=row['track_name'],
            artist=row['artist_name'],
            album=row['album_name'],
        )
        linked.append((event_id, int(row['id'])))
    if not linked:
        return 0
    try:
        with connect_sqlite(str(db_path)) as conn:
            conn.executemany(
                f'UPDATE {TABLE} SET listening_event_id=? WHERE id=?', linked
            )
    except sqlite3.Error as exc:
        logger.warning('last.fm history link save failed: {}', exc)
        return 0
    return len(linked)


def _load_state(db_path: Any) -> dict[str, Any]:
    with connect_sqlite(str(db_path), row_factory=True) as conn:
        row = conn.execute(
            'SELECT newest_at, oldest_at, backfill_done '
            "FROM history_import_state WHERE source='lastfm'"
        ).fetchone()
    if row is None:
        return {'newest_at': '', 'oldest_at': '', 'backfill_done': False}
    return {
        'newest_at': row['newest_at'],
        'oldest_at': row['oldest_at'],
        'backfill_done': bool(row['backfill_done']),
    }


def _save_state(db_path: Any, state: dict[str, Any]) -> None:
    with connect_sqlite(str(db_path)) as conn:
        conn.execute(
            'INSERT INTO history_import_state '
            '(source, newest_at, oldest_at, backfill_done) '
            "VALUES ('lastfm', ?, ?, ?) "
            'ON CONFLICT(source) DO UPDATE SET '
            'newest_at=excluded.newest_at, oldest_at=excluded.oldest_at, '
            'backfill_done=excluded.backfill_done',
            (
                state['newest_at'],
                state['oldest_at'],
                int(bool(state['backfill_done'])),
            ),
        )


def _uts_from_iso(value: str) -> Optional[int]:
    if not value:
        return None
    return int(datetime.fromisoformat(value).timestamp())


def _store_page(
    db_path: Any,
    rows: list[dict[str, Any]],
    listening: Any,
    user_id: int,
    state: dict[str, Any],
) -> tuple[int, int]:
    saved = save_recent_tracks(db_path, rows, user_id=user_id)
    linked = link_pending(db_path, listening, user_id=user_id)
    if rows:
        stamps = [row['played_at'] for row in rows]
        state['newest_at'] = (
            max([state['newest_at'], *stamps])
            if state['newest_at']
            else max(stamps)
        )
        state['oldest_at'] = (
            min([state['oldest_at'], *stamps])
            if state['oldest_at']
            else min(stamps)
        )
        _save_state(db_path, state)
    return saved, linked


def run_once(
    settings: Any,
    db_path: Any,
    *,
    listening: Any = None,
    user_id: int = 0,
    max_pages: int = 20,
    request: Optional[Request] = None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        'enabled': import_enabled(settings),
        'fetched': 0,
        'saved': 0,
        'linked': 0,
        'pages': 0,
        'error': '',
    }
    if not summary['enabled']:
        return summary
    config = read_config(settings)
    if config is None:
        summary['error'] = 'not_connected'
        return summary
    _connect(db_path).close()
    state = _load_state(db_path)
    newest = _uts_from_iso(state['newest_at'])
    body = fetch_recent_tracks(
        config,
        from_uts=newest + 1 if newest is not None else None,
        limit=MAX_LIMIT,
        request=request,
    )
    if body is None:
        summary['error'] = 'fetch_failed'
        return summary
    rows = parse_plays(body)
    summary['fetched'] += len(rows)
    saved, linked = _store_page(db_path, rows, listening, user_id, state)
    summary['saved'] += saved
    summary['linked'] += linked
    pages = 1 if rows else 0
    while not state['backfill_done'] and pages < max(1, int(max_pages)):
        oldest = _uts_from_iso(state['oldest_at'])
        if oldest is None:
            break
        body = fetch_recent_tracks(
            config, to_uts=oldest - 1, limit=MAX_LIMIT, request=request
        )
        if body is None:
            summary['error'] = 'fetch_failed'
            break
        rows = parse_plays(body)
        summary['fetched'] += len(rows)
        if not rows:
            state['backfill_done'] = True
            _save_state(db_path, state)
            break
        saved, linked = _store_page(db_path, rows, listening, user_id, state)
        summary['saved'] += saved
        summary['linked'] += linked
        pages += 1
    summary['pages'] = pages
    return summary


async def lastfm_history_loop(
    cfg_getter: Callable[[], Any],
    db_path: Any,
    *,
    listening_getter: Optional[Callable[[], Any]] = None,
    user_id_getter: Optional[Callable[[], int]] = None,
    idle_seconds: float = 900,
    max_pages: int = 20,
    request: Optional[Request] = None,
) -> None:
    while True:
        try:
            summary = await asyncio.to_thread(
                run_once,
                cfg_getter(),
                db_path,
                listening=(
                    listening_getter()
                    if listening_getter is not None
                    else None
                ),
                user_id=user_id_getter() if user_id_getter is not None else 0,
                max_pages=max_pages,
                request=request,
            )
            if summary['saved']:
                logger.info(
                    'last.fm history: stored {} new play(s)', summary['saved']
                )
            elif summary['error']:
                logger.debug(
                    'last.fm history: nothing stored ({})', summary['error']
                )
        except Exception:  # noqa: BLE001 - a loop must survive everything
            logger.exception('last.fm history loop failed')
        await asyncio.sleep(idle_seconds)
