"""Spotify playback-context parsing and persistent display-name cache."""

from __future__ import annotations

import asyncio
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional
from urllib.parse import urlparse

from loguru import logger

from . import spotify_mirror
from .sqlite_utils import connect_sqlite

TABLE = 'spotify_context_cache'
_KINDS = {'playlist', 'artist', 'album'}
_NAME_TTL = timedelta(days=30)
_ERROR_RETRY = timedelta(hours=6)
_NOT_FOUND_RETRY = timedelta(hours=24)

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


def _stamp(value: Any) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(str(value or ''))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _pending_contexts(db_path: Any, limit: int) -> list[str]:
    if not Path(db_path).is_file():
        return []
    ensure_schema(db_path)
    now = datetime.now(timezone.utc)
    with connect_sqlite(str(db_path), row_factory=True) as conn:
        contexts = conn.execute(
            'SELECT e.context, MIN(e.played_at) AS oldest '
            'FROM listening_events e JOIN listening_event_sources s '
            'ON s.event_id=e.id AND s.source=? '
            "WHERE e.context != '' GROUP BY e.context "
            'ORDER BY oldest, e.context',
            ('spotify',),
        ).fetchall()
        cached = {
            str(row['context_key']): row
            for row in conn.execute(f'SELECT * FROM {TABLE}')
        }
    pending: list[str] = []
    seen: set[str] = set()
    for row in contexts:
        key = normalize_context(row['context'])
        if not key or key in seen:
            continue
        seen.add(key)
        entry = cached.get(key)
        if entry is not None:
            retry_at = _stamp(entry['retry_at'])
            if retry_at and retry_at > now:
                continue
            fetched_at = _stamp(entry['fetched_at'])
            if (
                str(entry['name'] or '').strip()
                and fetched_at
                and now - fetched_at < _NAME_TTL
            ):
                continue
        pending.append(key)
        if len(pending) >= max(1, int(limit)):
            break
    return pending


def _cache_error(
    db_path: Any,
    context_key: str,
    error: str,
    retry_after: timedelta,
) -> None:
    key = normalize_context(context_key)
    if not key:
        return
    ensure_schema(db_path)
    with connect_sqlite(str(db_path)) as conn:
        conn.execute(
            f'INSERT INTO {TABLE} '
            '(context_key, kind, name, fetched_at, last_error, retry_at) '
            "VALUES (?, ?, '', '', ?, ?) "
            'ON CONFLICT(context_key) DO UPDATE SET '
            'last_error=excluded.last_error, retry_at=excluded.retry_at',
            (
                key,
                context_kind(key),
                str(error or 'unknown_error')[:160],
                (datetime.now(timezone.utc) + retry_after).isoformat(),
            ),
        )


def _retry_after(response: Any) -> float:
    headers = getattr(response, 'headers', None) or {}
    try:
        return max(0.0, float(headers.get('Retry-After') or 0))
    except (TypeError, ValueError):
        return 0.0


def _mirror_config(settings: Any) -> Optional[dict[str, Any]]:
    block = (
        settings.get('spotify_mirror') if isinstance(settings, dict) else None
    )
    if not isinstance(block, dict) or not block.get('enabled'):
        return None
    if not str(block.get('client_id') or '').strip():
        return None
    if not (
        str(block.get('access_token') or '').strip()
        or str(block.get('refresh_token') or '').strip()
    ):
        return None
    return dict(block)


def run_once(
    settings: Any,
    db_path: Any,
    *,
    limit: int = 25,
    request: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Resolve a bounded batch of canonical Spotify context names."""

    summary: dict[str, Any] = {
        'enabled': False,
        'examined': 0,
        'resolved': 0,
        'failed': 0,
        'rate_limited': False,
        'retry_after': 0,
        'tokens': {},
    }
    config = _mirror_config(settings)
    if config is None:
        return summary
    summary['enabled'] = True
    current = spotify_mirror.ensure_token(config, request=request)
    if current is None:
        summary['error'] = 'auth_failed'
        return summary
    if current.get('access_token') != config.get('access_token'):
        summary['tokens'] = {
            'access_token': current.get('access_token', ''),
            'refresh_token': current.get('refresh_token', ''),
            'token_expires_at': current.get('token_expires_at', 0),
        }
    pending = _pending_contexts(db_path, limit)
    summary['examined'] = len(pending)
    sender = request or spotify_mirror._request
    token = str(current.get('access_token') or '')
    for index, key in enumerate(pending):
        _prefix, kind, resource_id = key.split(':', 2)
        url = f'{spotify_mirror.SPOTIFY_API}/{kind}s/{resource_id}'
        try:
            response = sender(
                'GET', url, headers=spotify_mirror._bearer(token)
            )
            status = int(getattr(response, 'status_code', 200) or 200)
            if status == 429:
                delay = _retry_after(response)
                summary['rate_limited'] = True
                summary['retry_after'] = delay
                summary['failed'] += 1
                _cache_error(
                    db_path, key, 'rate_limited', timedelta(seconds=delay)
                )
                break
            if status in {401, 403}:
                summary['failed'] += 1
                summary['stopped'] = status
                _cache_error(db_path, key, f'http_{status}', _ERROR_RETRY)
                break
            if status == 404:
                summary['failed'] += 1
                _cache_error(db_path, key, 'http_404', _NOT_FOUND_RETRY)
                continue
            if status >= 400:
                summary['failed'] += 1
                _cache_error(db_path, key, f'http_{status}', _ERROR_RETRY)
                continue
            body = response.json()
            name = (
                str(body.get('name') or '').strip()
                if isinstance(body, dict)
                else ''
            )
            if not name:
                summary['failed'] += 1
                _cache_error(db_path, key, 'missing_name', _ERROR_RETRY)
                continue
            cache_name(db_path, key, name)
            summary['resolved'] += 1
        except Exception as exc:  # noqa: BLE001 - background best-effort
            summary['failed'] += 1
            _cache_error(db_path, key, type(exc).__name__, _ERROR_RETRY)
        if index + 1 < len(pending):
            time.sleep(1.0)
    return summary


async def spotify_context_loop(
    cfg_getter: Callable[[], Any],
    db_path: Any,
    *,
    idle_seconds: float = 900,
    limit: int = 25,
    request: Optional[Callable[..., Any]] = None,
    persist_tokens: Optional[Callable[[dict[str, Any]], Any]] = None,
) -> None:
    """Periodically resolve names without making Stats wait for Spotify."""

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
            if tokens and persist_tokens is not None:
                await asyncio.to_thread(persist_tokens, tokens)
            if summary.get('resolved'):
                logger.info(
                    'Spotify context: resolved {} name(s)', summary['resolved']
                )
        except Exception:  # noqa: BLE001 - loop must survive everything
            logger.exception('Spotify context resolver loop failed')
        await asyncio.sleep(idle_seconds)
