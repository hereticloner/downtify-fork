"""The user's Spotify listening history, read once and kept locally.

Spotify already knows everything the user played and when; the Web API
will hand that over through ``GET /v1/me/player/recently-played`` -
50 entries per call, newest first, with the track id, names and
duration. This module pulls that page on a slow timer and stores it, so
"what did I listen to" can be answered from Downtify without asking
Spotify again (the endpoint only reaches back a few hundred entries, and
asks nothing more than that window).

It reuses the OAuth connection the Spotify Mirror owns
(``downtify.spotify_mirror``): the same client id and tokens, the same
``ensure_token`` refresh, nothing new to connect. Nothing is fetched
unless the user turns on ``import_recent`` in the ``spotify_mirror``
settings block, and every failure is logged - a history import that
cannot run is not a reason to stop running.

The stored rows are plain plays, not library entries: they are never
written into the catalog, never tagged onto a file and never deleted.
One table (``spotify_recently_played``) in the activity database, keyed
by ``played_at`` so the same play arriving in two consecutive fetches
lands once (the endpoint overlaps windows on purpose).
"""

from __future__ import annotations

import asyncio
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import httpx
from loguru import logger

from . import spotify_mirror
from .sqlite_utils import connect_sqlite

#: The settings block the switch lives in.
SETTINGS_KEY = 'spotify_mirror'
#: The switch that turns the import on (off unless the user says so).
IMPORT_FLAG = 'import_recent'
RECENTLY_PLAYED_PATH = '/me/player/recently-played'
TABLE = 'spotify_recently_played'

DEFAULT_LIMIT = 50
#: What the Web API accepts for this endpoint; a larger ask is clamped
#: rather than sent, because Spotify answers 400 and the whole sweep
#: would be lost.
MAX_LIMIT = 50
#: How often the loop sweeps. The endpoint returns a window that
#: overlaps by design, so this is a backstop against a missed play, not
#: a sampling rate.
IDLE_SECONDS = 1800
#: Longest a 429 is waited out before the iteration is given up on.
MAX_BACKOFF_SECONDS = 60.0

_CREATE_TABLE = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    played_at TEXT PRIMARY KEY,
    track_name TEXT NOT NULL DEFAULT '',
    artist_name TEXT NOT NULL DEFAULT '',
    album_name TEXT NOT NULL DEFAULT '',
    spotify_track_id TEXT NOT NULL DEFAULT '',
    duration_ms INTEGER NOT NULL DEFAULT 0,
    synced_at TEXT NOT NULL DEFAULT ''
)
"""

_INSERT = f"""
INSERT OR IGNORE INTO {TABLE} (
    played_at, track_name, artist_name, album_name,
    spotify_track_id, duration_ms, synced_at
) VALUES (?, ?, ?, ?, ?, ?, ?)
"""

_SELECT = f"""
SELECT played_at, track_name, artist_name, album_name,
       spotify_track_id, duration_ms, synced_at
FROM {TABLE} ORDER BY played_at DESC LIMIT ?
"""

#: Request seam: tests inject a fake; the default is a plain httpx call.
Request = Callable[..., Any]
#: ``(tokens) -> None`` - persists a token the sweep renewed.
PersistTokens = Callable[[dict[str, Any]], Any]


def _text(value: Any) -> str:
    return str(value or '').strip()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _request(
    method: str,
    url: str,
    *,
    headers: Optional[dict[str, str]] = None,
    params: Optional[dict[str, Any]] = None,
):
    return httpx.request(
        method,
        url,
        headers=headers,
        params=params,
        timeout=spotify_mirror.TIMEOUT_SECONDS,
    )


# ── the switch ───────────────────────────────────────────────────────


def import_enabled(settings: Any) -> bool:
    """Whether the mirror is on *and* the history import is turned on."""

    block = settings.get(SETTINGS_KEY) if isinstance(settings, dict) else None
    return bool(
        isinstance(block, dict)
        and block.get('enabled')
        and block.get(IMPORT_FLAG)
    )


def credentials(settings: Any) -> Optional[dict[str, str]]:
    """The Mirror's OAuth credentials when the import can run, else ``None``."""

    if not import_enabled(settings):
        return None
    block = settings.get(SETTINGS_KEY)
    return spotify_mirror.mirror_credentials(block)


# ── reading Spotify ──────────────────────────────────────────────────


def clamp_limit(limit: Any) -> int:
    """Coerce a requested page size to what the endpoint accepts."""

    try:
        value = int(limit)
    except (TypeError, ValueError):
        return DEFAULT_LIMIT
    return min(MAX_LIMIT, max(1, value))


def _duration_ms(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _artists(track: dict[str, Any]) -> str:
    names = [
        _text(artist.get('name'))
        for artist in track.get('artists') or []
        if isinstance(artist, dict)
    ]
    return ', '.join(name for name in names if name)


def parse_plays(body: Any) -> list[dict[str, Any]]:
    """Rows from a ``recently-played`` body, oldest-first when stored.

    Spotify returns newest-first; the store is read newest-first too, so
    the order is left as sent and the reader sorts. Rows without a
    timestamp or a track id are dropped: they have no key to dedupe on
    and nothing to show.
    """

    items = body.get('items') if isinstance(body, dict) else None
    rows: list[dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        # The endpoint wraps each row as ``track``; newer Web API
        # responses use ``item``. Accept both so a shape change doesn't
        # silently read nothing.
        track = item.get('track') or item.get('item')
        if not isinstance(track, dict):
            continue
        played_at = _text(item.get('played_at'))
        track_id = _text(track.get('id'))
        if not played_at or not track_id:
            continue
        album = track.get('album')
        rows.append({
            'played_at': played_at,
            'track_name': _text(track.get('name')),
            'artist_name': _artists(track),
            'album_name': _text(album.get('name'))
            if isinstance(album, dict)
            else '',
            'spotify_track_id': track_id,
            'duration_ms': _duration_ms(track.get('duration_ms')),
        })
    return rows


def _retry_after(response: Any) -> float:
    """Seconds to wait after a 429, from its ``Retry-After`` header."""

    headers = getattr(response, 'headers', None)
    raw = ''
    if headers is not None:
        try:
            raw = str(headers.get('Retry-After') or '').strip()
        except AttributeError:
            raw = ''
    try:
        return max(0.0, min(MAX_BACKOFF_SECONDS, float(raw)))
    except ValueError:
        return MAX_BACKOFF_SECONDS


def _write_back(config: dict[str, Any], current: dict[str, Any]) -> None:
    config['access_token'] = current.get('access_token', '')
    config['refresh_token'] = current.get('refresh_token', '')
    config['token_expires_at'] = current.get('token_expires_at', '')


def fetch_recently_played(
    config: dict[str, Any],
    *,
    request: Optional[Request] = None,
    limit: int = DEFAULT_LIMIT,
) -> Optional[list[dict[str, Any]]]:
    """The user's last plays, or ``None`` when they can't be read.

    Uses the mirror's tokens; a stale access token is renewed through
    ``spotify_mirror.ensure_token`` and the renewed fields are written
    back onto *config* so the caller can persist them. Any failure - no
    working token, an HTTP error, a non-JSON body - is logged and
    reported as ``None``. A 429 waits out its ``Retry-After`` (capped)
    and gives up on the iteration rather than hammering the endpoint.
    """

    current = spotify_mirror.ensure_token(config, request=request)
    if current is None:
        logger.warning(
            'Spotify history: no working token - reconnect Spotify in '
            'Settings to grant the listening-history scope'
        )
        return None
    # Hand the caller the possible renewal; it owns persistence.
    _write_back(config, current)

    sender = request or _request
    url = f'{spotify_mirror.SPOTIFY_API}{RECENTLY_PLAYED_PATH}'
    token = str(current.get('access_token') or '')
    response = None
    try:
        response = sender(
            'GET',
            url,
            headers=spotify_mirror._bearer(token),
            params={'limit': clamp_limit(limit)},
        )
        status = int(getattr(response, 'status_code', 200) or 200)
        if status == 429:
            delay = _retry_after(response)
            logger.warning(
                'Spotify history: rate limited, waiting {}s before giving '
                'up this pass',
                delay,
            )
            time.sleep(delay)
            return None
        if status == 403:
            logger.warning(
                'Spotify history: Spotify refused the request - reconnect '
                'Spotify in Settings so the new scope is granted'
            )
            return None
        response.raise_for_status()
        body = response.json()
    except Exception as exc:  # noqa: BLE001 - reported to the log, not raised
        logger.warning('Spotify history: fetch failed: {}', exc)
        return None
    return parse_plays(body)


# ── the local store ──────────────────────────────────────────────────


def _connect(db_path: Any) -> sqlite3.Connection:
    path = Path(db_path)
    parent = path.parent
    if str(parent):
        parent.mkdir(parents=True, exist_ok=True)
    conn = connect_sqlite(str(path))
    conn.execute(_CREATE_TABLE)
    return conn


def save_recently_played(db_path: Any, rows: Any) -> int:
    """Store *rows*, ignoring the ones already there; how many landed.

    ``INSERT OR IGNORE`` on the ``played_at`` key is what makes the
    overlapping windows the endpoint returns cheap: the same play
    arriving in the next fetch is a no-op instead of a second row.
    Rows missing the key are dropped rather than stored.
    """

    clean = [
        (
            _text(row.get('played_at')),
            _text(row.get('track_name')),
            _text(row.get('artist_name')),
            _text(row.get('album_name')),
            _text(row.get('spotify_track_id')),
            _duration_ms(row.get('duration_ms')),
            _text(row.get('synced_at')) or _now_iso(),
        )
        for row in rows or []
        if isinstance(row, dict) and _text(row.get('played_at'))
    ]
    if not clean:
        return 0
    conn = _connect(db_path)
    try:
        before = conn.total_changes
        conn.executemany(_INSERT, clean)
        conn.commit()
        return conn.total_changes - before
    except sqlite3.Error as exc:
        logger.warning('Spotify history: could not store plays: {}', exc)
        return 0
    finally:
        conn.close()


def get_recent_from_spotify(
    db_path: Any, limit: int = DEFAULT_LIMIT
) -> list[dict[str, Any]]:
    """Stored plays, newest first; ``[]`` when there are none yet.

    A missing database is not an error - the table is created by the
    first successful sweep, and a server that never imported history has
    nothing to report (and, reading, doesn't create an empty file
    either).
    """

    if not Path(db_path).is_file():
        return []
    try:
        conn = connect_sqlite(str(db_path))
    except sqlite3.Error as exc:
        logger.warning('Spotify history: could not read stored plays: {}', exc)
        return []
    try:
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(_SELECT, (clamp_limit(limit),)).fetchall()
        except sqlite3.OperationalError:
            # No table yet: nothing was ever imported.
            return []
    finally:
        conn.close()
    return [dict(row) for row in rows]


def count_plays(db_path: Any) -> int:
    """How many plays are stored; ``0`` when there are none yet."""

    if not Path(db_path).is_file():
        return 0
    try:
        conn = connect_sqlite(str(db_path))
    except sqlite3.Error:
        return 0
    try:
        return int(conn.execute(f'SELECT COUNT(*) FROM {TABLE}').fetchone()[0])
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


# ── the periodic sweep ───────────────────────────────────────────────


def run_once(
    settings: Any,
    db_path: Any,
    *,
    limit: int = DEFAULT_LIMIT,
    request: Optional[Request] = None,
) -> dict[str, Any]:
    """One sweep: read the page, store what's new. Never raises.

    Returns a small summary - what the switch said, how many rows landed
    and, when the token was renewed, the fields to persist - so the loop
    can log a line and the caller can save the renewal.
    """

    summary: dict[str, Any] = {
        'enabled': import_enabled(settings),
        'fetched': 0,
        'saved': 0,
        'error': '',
        'tokens': {},
    }
    if not summary['enabled']:
        return summary
    config = credentials(settings)
    if not config or not config.get('client_id'):
        summary['error'] = 'not_connected'
        return summary
    before_token = config.get('access_token')
    rows = fetch_recently_played(config, request=request, limit=limit)
    if rows is None:
        summary['error'] = 'fetch_failed'
        return summary
    summary['fetched'] = len(rows)
    summary['saved'] = save_recently_played(db_path, rows)
    if config.get('access_token') != before_token:
        summary['tokens'] = {
            'access_token': config.get('access_token', ''),
            'refresh_token': config.get('refresh_token', ''),
            'token_expires_at': config.get('token_expires_at', ''),
        }
    return summary


async def spotify_history_loop(
    cfg_getter: Callable[[], Any],
    db_path: Any,
    *,
    idle_seconds: float = IDLE_SECONDS,
    limit: int = DEFAULT_LIMIT,
    request: Optional[Request] = None,
    persist_tokens: Optional[PersistTokens] = None,
) -> None:
    """Background task: sweep listening history while the switch is on.

    Idles cheaply: with the import off (the default) or Spotify not
    connected it never touches the API. A failed sweep - a token that
    can't be renewed, a 429, an HTTP error - is logged and skipped, and
    the next iteration tries again; the loop itself never dies.
    """

    while True:
        try:
            summary = await asyncio.to_thread(
                run_once,
                cfg_getter(),
                db_path,
                limit=limit,
                request=request,
            )
            tokens = summary.pop('tokens', None)
            if persist_tokens is not None and tokens:
                await asyncio.to_thread(persist_tokens, tokens)
            if summary['saved']:
                logger.info(
                    'Spotify history: stored {} new play(s)', summary['saved']
                )
            elif summary['error']:
                logger.debug(
                    'Spotify history: nothing stored ({})', summary['error']
                )
        except Exception:  # noqa: BLE001 - a loop must survive everything
            logger.exception('Spotify history loop failed')
        await asyncio.sleep(idle_seconds)
