"""Scrobble plays to last.fm.

A player reports what it plays to ``POST /api/activity/playback`` (see
:mod:`downtify.account_routes`); a report that reaches the scrobble
threshold is sent here. A track counts once it has played for at least
half its length or four minutes, whichever comes first, and never for a
track shorter than 30 seconds - last.fm's own rule.

Only last.fm is supported. The API key and secret come from the user's
last.fm API account; the session key is obtained through the in-app auth
flow (:func:`get_token`, the user approves on last.fm, then
:func:`get_session`) so nobody has to paste a session key by hand.

Everything is best-effort: a call that fails is logged and answered with
a falsy value, never raised, so a last.fm hiccup can't fail the player's
report. Signing follows last.fm's rule - every parameter except
``format`` and ``callback`` sorted by name, concatenated as ``namevalue``,
and the API secret appended, hashed with MD5.
"""

from __future__ import annotations

import hashlib
import threading
import time
from typing import Any, Optional

import httpx
from loguru import logger

LASTFM_API = 'https://ws.audioscrobbler.com/2.0/'
AUTH_URL = 'https://www.last.fm/api/auth/'
TIMEOUT_SECONDS = 6.0
# last.fm ignores shorter tracks; a play counts at half the length or four
# minutes, whichever comes first.
MIN_DURATION_SECONDS = 30
MAX_THRESHOLD_SECONDS = 240


def _text(value: Any) -> str:
    return str(value or '').strip()


def lastfm_credentials(block: Any) -> Optional[dict[str, str]]:
    """The API key and secret from a scrobbling block, or ``None``.

    The session key is included when present, but not required: the auth
    flow needs a key and secret before there is a session.
    """

    if not isinstance(block, dict):
        return None
    api_key = _text(block.get('lastfm_api_key'))
    api_secret = _text(block.get('lastfm_api_secret'))
    if not api_key or not api_secret:
        return None
    return {
        'api_key': api_key,
        'api_secret': api_secret,
        'session_key': _text(block.get('lastfm_session_key')),
    }


def active_lastfm_config(settings: Any) -> Optional[dict[str, Any]]:
    """The config scrobbling needs, or ``None`` when it can't run.

    Requires the master switch, the last.fm switch and a session key, so
    a player report with scrobbling half-configured is a silent no-op.
    """

    if not isinstance(settings, dict):
        return None
    block = settings.get('scrobbling')
    if not isinstance(block, dict):
        return None
    if not block.get('enabled') or not block.get('lastfm_enabled'):
        return None
    credentials = lastfm_credentials(block)
    if credentials is None or not credentials['session_key']:
        return None
    credentials['now_playing'] = bool(block.get('scrobble_now_playing', True))
    return credentials


def _signature(params: dict[str, Any], api_secret: str) -> str:
    """last.fm's ``api_sig``: sorted ``namevalue`` pairs + secret, MD5."""

    parts = []
    for name in sorted(params):
        if name in {'format', 'callback'}:
            continue
        value = params[name]
        if not value:
            continue
        parts.append(f'{name}{value}')
    raw = ''.join(parts) + api_secret
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


def _post(url: str, data: dict[str, Any], timeout: float):
    return httpx.post(url, data=data, timeout=timeout)


def _call(
    method: str,
    params: dict[str, Any],
    config: dict[str, Any],
    *,
    post: Any = None,
) -> dict[str, Any]:
    """A signed last.fm call; ``{}`` when it fails for any reason."""

    payload: dict[str, Any] = {'method': method, 'api_key': config['api_key']}
    for name, value in params.items():
        if value:
            payload[name] = value
    payload['format'] = 'json'
    payload['api_sig'] = _signature(payload, config['api_secret'])
    sender = post or _post
    try:
        response = sender(LASTFM_API, payload, TIMEOUT_SECONDS)
        response.raise_for_status()
        body = response.json()
    except Exception as exc:  # noqa: BLE001 - best-effort by design
        logger.warning('last.fm {} failed: {}', method, exc)
        return {}
    return body if isinstance(body, dict) else {}


def track_params(track: Any) -> Optional[dict[str, str]]:
    """Map a reported track to last.fm's naming, or ``None`` if unnamed."""

    if not isinstance(track, dict):
        return None
    artist = _text(track.get('artist'))
    title = _text(track.get('title'))
    if not artist or not title:
        return None
    params = {'artist': artist, 'track': title}
    album = _text(track.get('album'))
    if album:
        params['album'] = album
    try:
        duration = int(float(track.get('duration') or 0))
    except (TypeError, ValueError):
        duration = 0
    if duration > 0:
        params['duration'] = str(duration)
    return params


def scrobble_threshold(duration: Any) -> float:
    """Seconds a track must play to count; ``0`` when it's too short."""

    try:
        seconds = float(duration or 0)
    except (TypeError, ValueError):
        return 0.0
    if seconds < MIN_DURATION_SECONDS:
        return 0.0
    return min(seconds / 2.0, MAX_THRESHOLD_SECONDS)


def is_scrobbleable(track: Any, position: Any) -> bool:
    """Whether *position* has reached this track's scrobble threshold."""

    if not isinstance(track, dict):
        return False
    threshold = scrobble_threshold(track.get('duration'))
    if threshold <= 0:
        return False
    try:
        played = float(position or 0)
    except (TypeError, ValueError):
        return False
    return played >= threshold


def update_now_playing(
    track: Any, config: dict[str, Any], *, post: Any = None
) -> bool:
    """Tell last.fm what is playing (signed); ``False`` when unnamed."""

    params = track_params(track)
    if params is None:
        return False
    return bool(
        _call(
            'track.updateNowPlaying',
            {**params, 'sk': config['session_key']},
            config,
            post=post,
        )
    )


def scrobble(
    track: Any,
    config: dict[str, Any],
    *,
    timestamp: Any = None,
    post: Any = None,
) -> bool:
    """Scrobble one play of *track* (signed); ``False`` when unnamed."""

    params = track_params(track)
    if params is None:
        return False
    try:
        when = int(timestamp if timestamp is not None else time.time())
    except (TypeError, ValueError):
        when = int(time.time())
    return bool(
        _call(
            'track.scrobble',
            {**params, 'timestamp': str(when), 'sk': config['session_key']},
            config,
            post=post,
        )
    )


def build_auth_url(api_key: str, token: str) -> str:
    return f'{AUTH_URL}?api_key={api_key}&token={token}'


def get_token(config: dict[str, Any], *, post: Any = None) -> Optional[str]:
    """Ask last.fm for a request token (step 1 of the auth flow)."""

    payload = _call('auth.getToken', {}, config, post=post)
    token = _text(payload.get('token'))
    return token or None


def get_session(
    config: dict[str, Any], token: str, *, post: Any = None
) -> Optional[dict[str, str]]:
    """Trade an approved token for a session key (step 3)."""

    payload = _call('auth.getSession', {'token': token}, config, post=post)
    session = payload.get('session')
    if not isinstance(session, dict):
        return None
    key = _text(session.get('key'))
    if not key:
        return None
    return {'session_key': key, 'username': _text(session.get('name'))}


def check_connection(
    config: dict[str, Any], *, post: Any = None
) -> dict[str, Any]:
    """Check a session key via ``user.getInfo``; ``{ok, username?|error}``."""

    if not isinstance(config, dict) or not _text(config.get('session_key')):
        return {'ok': False, 'error': 'missing_credentials'}
    if not _text(config.get('api_key')) or not _text(config.get('api_secret')):
        return {'ok': False, 'error': 'missing_credentials'}
    payload = _call(
        'user.getInfo', {'sk': config['session_key']}, config, post=post
    )
    user = payload.get('user')
    if isinstance(user, dict) and _text(user.get('name')):
        return {'ok': True, 'username': _text(user.get('name'))}
    return {'ok': False, 'error': 'auth_failed'}


class ScrobbleTracker:
    """In-memory: which player already got a now-playing and a scrobble.

    Keeps a report that repeats the same song from spamming last.fm. A
    player that switches songs (or a user that signs out) starts fresh.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._now_playing: dict[tuple[int, str], str] = {}
        self._scrobbled: dict[tuple[int, str], str] = {}

    def should_send_now_playing(
        self, user_id: int, player: str, song: str
    ) -> bool:
        key = (int(user_id), player)
        with self._lock:
            if self._now_playing.get(key) == song:
                return False
            self._now_playing[key] = song
            return True

    def should_scrobble(self, user_id: int, player: str, song: str) -> bool:
        key = (int(user_id), player)
        with self._lock:
            if self._scrobbled.get(key) == song:
                return False
            self._scrobbled[key] = song
            return True

    def forget_user(self, user_id: int) -> None:
        with self._lock:
            for store in (self._now_playing, self._scrobbled):
                for key in [k for k in store if k[0] == user_id]:
                    del store[key]
