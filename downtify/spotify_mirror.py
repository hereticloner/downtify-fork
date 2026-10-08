"""Mirror plays to Spotify Connect: Downtify listening shows up on
Spotify - "Recently played", Friend Activity, the year wrap-up.

Spotify only records real playback; nothing can inject listening
history (and the private endpoints that try are an account-ban risk).
What the documented Web API can do is ask the user's own Premium
account to play the same track on a Spotify Connect device. This fork
ships one on the server: the "Downtify Mirror" spotifyd container,
silent (volume 0) and always online. A play in Downtify starts the same
song there, and Spotify counts it like any other playback.

Only a track's START is mirrored - the same ``started`` signal
scrobbling uses - deduped per player and song, so a scrub or a
pause/resume doesn't spam the API. Everything is best-effort: a mirror
failure is logged and dropped, never raised, and never touches the
playback that triggered it.

OAuth is Authorization Code + PKCE (no client secret needed): the user
creates their own Spotify app, points its redirect URI at this server,
connects in Settings → Spotify Mirror, and the tokens are stored in the
``spotify_mirror`` settings block. Scopes are playback ones only:
``user-read-playback-state``, ``user-modify-playback-state``,
``user-read-currently-playing``.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import threading
import time
from typing import Any, Callable, Optional
from urllib.parse import quote

import httpx
from loguru import logger

SPOTIFY_ACCOUNTS = 'https://accounts.spotify.com'
SPOTIFY_API = 'https://api.spotify.com/v1'
TOKEN_PATH = '/api/token'
AUTHORIZE_PATH = '/authorize'
TIMEOUT_SECONDS = 6.0
# Seconds before expiry at which an access token counts as stale.
TOKEN_REFRESH_MARGIN = 30
SCOPES = (
    'user-read-playback-state user-modify-playback-state '
    'user-read-currently-playing'
)

#: Request seam: tests inject a fake; the default is a plain httpx call.
Request = Callable[..., Any]


def _text(value: Any) -> str:
    return str(value or '').strip()


def mirror_credentials(block: Any) -> Optional[dict[str, str]]:
    """Client id and tokens from a ``spotify_mirror`` block, or ``None``.

    The client id is required; tokens aren't (the connect flow needs a
    client id before any token exists).
    """

    if not isinstance(block, dict):
        return None
    client_id = _text(block.get('client_id'))
    if not client_id:
        return None
    return {
        'client_id': client_id,
        'access_token': _text(block.get('access_token')),
        'refresh_token': _text(block.get('refresh_token')),
        'device_id': _text(block.get('device_id')),
    }


def active_mirror_config(settings: Any) -> Optional[dict[str, Any]]:
    """The config mirroring needs, or ``None`` when it can't run.

    Requires the switch, a client id, a working token (the access one
    while fresh, else the refresh token to renew it) and a device id.
    """

    if not isinstance(settings, dict):
        return None
    block = settings.get('spotify_mirror')
    if not isinstance(block, dict) or not block.get('enabled'):
        return None
    credentials = mirror_credentials(block)
    if credentials is None:
        return None
    if not credentials['device_id']:
        return None
    try:
        expires_at = float(block.get('token_expires_at') or 0)
    except (TypeError, ValueError):
        expires_at = 0
    fresh = (
        credentials['access_token']
        and expires_at - TOKEN_REFRESH_MARGIN > time.time()
    )
    if not fresh and not credentials['refresh_token']:
        return None
    return {
        **credentials,
        'token_expires_at': expires_at,
        'silent_on_target': bool(block.get('silent_on_target', True)),
    }


def _request(
    method: str,
    url: str,
    *,
    headers: Optional[dict[str, str]] = None,
    params: Optional[dict[str, Any]] = None,
    json: Optional[dict[str, Any]] = None,
    data: Optional[dict[str, Any]] = None,
):
    return httpx.request(
        method,
        url,
        headers=headers,
        params=params,
        json=json,
        data=data,
        timeout=TIMEOUT_SECONDS,
    )


def pkce_pair() -> tuple[str, str]:
    """A ``(code_verifier, code_challenge)`` pair for PKCE (RFC 7636)."""

    verifier = (
        base64.urlsafe_b64encode(secrets.token_bytes(64)).decode().rstrip('=')
    )
    challenge = (
        base64
        .urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .decode()
        .rstrip('=')
    )
    return verifier, challenge


def authorize_url(
    client_id: str, redirect_uri: str, state: str, code_challenge: str
) -> str:
    """The Spotify authorize page URL for the connect flow."""

    query = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'state': state,
        'code_challenge_method': 'S256',
        'code_challenge': code_challenge,
        'scope': SCOPES,
    }
    encoded = '&'.join(
        f'{key}={quote(str(value), safe="")}' for key, value in query.items()
    )
    return f'{SPOTIFY_ACCOUNTS}{AUTHORIZE_PATH}?{encoded}'


def _token_body(client_id: str, **fields: Any) -> dict[str, Any]:
    body = {'client_id': client_id}
    body.update(fields)
    return body


def _parse_tokens(
    body: dict[str, Any], previous: dict[str, Any], now: float
) -> Optional[dict[str, Any]]:
    """Normalize a token answer; ``None`` when it's not one."""

    if not isinstance(body, dict) or not body.get('access_token'):
        return None
    refresh = _text(body.get('refresh_token')) or previous.get(
        'refresh_token', ''
    )
    return {
        'access_token': _text(body['access_token']),
        'refresh_token': refresh,
        'token_expires_at': round(
            now + float(body.get('expires_in') or 3600), 3
        ),
    }


def exchange_code(
    client_id: str,
    code: str,
    redirect_uri: str,
    code_verifier: str,
    *,
    request: Optional[Request] = None,
    now: Optional[Callable[[], float]] = None,
) -> Optional[dict[str, Any]]:
    """Trade the authorized code for tokens; ``None`` when refused."""

    sender = request or _request
    try:
        response = sender(
            'POST',
            f'{SPOTIFY_ACCOUNTS}{TOKEN_PATH}',
            data=_token_body(
                client_id,
                grant_type='authorization_code',
                code=code,
                redirect_uri=redirect_uri,
                code_verifier=code_verifier,
            ),
        )
        response.raise_for_status()
        body = response.json()
    except Exception as exc:  # noqa: BLE001 - caller shows a clean error
        logger.warning('Spotify token exchange failed: {}', exc)
        return None
    return _parse_tokens(body, {}, (now or time.time)())


def refresh_access_token(
    client_id: str, refresh_token: str, *, request: Optional[Request] = None
) -> Optional[dict[str, Any]]:
    """Renew an access token; ``None`` when Spotify refuses."""

    if not refresh_token:
        return None
    sender = request or _request
    try:
        response = sender(
            'POST',
            f'{SPOTIFY_ACCOUNTS}{TOKEN_PATH}',
            data=_token_body(
                client_id,
                grant_type='refresh_token',
                refresh_token=refresh_token,
            ),
        )
        response.raise_for_status()
        body = response.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning('Spotify token refresh failed: {}', exc)
        return None
    return _parse_tokens(body, {'refresh_token': refresh_token}, time.time())


def ensure_token(
    config: dict[str, Any], *, request: Optional[Request] = None
) -> Optional[dict[str, Any]]:
    """A config with a fresh access token, refreshing when stale.

    Returns ``None`` when nothing works. A refreshed token is returned
    with the new fields - the caller persists it in settings.
    """

    expires_at = float(config.get('token_expires_at') or 0)
    fresh = (
        config.get('access_token')
        and expires_at - TOKEN_REFRESH_MARGIN > time.time()
    )
    if fresh:
        return config
    renewed = refresh_access_token(
        config['client_id'], config.get('refresh_token', ''), request=request
    )
    if not renewed:
        return None
    return {**config, **renewed}


def _bearer(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


def list_devices(
    config: dict[str, Any], *, request: Optional[Request] = None
) -> list[dict[str, Any]]:
    """Spotify Connect devices on the account, ``[]`` on any failure."""

    current = ensure_token(config, request=request)
    if current is None:
        return []
    sender = request or _request
    try:
        response = sender(
            'GET',
            f'{SPOTIFY_API}/me/player/devices',
            headers=_bearer(current['access_token']),
        )
        response.raise_for_status()
        body = response.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning('Spotify device list failed: {}', exc)
        return []
    devices = body.get('devices') if isinstance(body, dict) else None
    if not isinstance(devices, list):
        return []
    return [
        {
            'id': _text(d.get('id')),
            'name': _text(d.get('name')),
            'is_active': bool(d.get('is_active')),
        }
        for d in devices
        if isinstance(d, dict) and _text(d.get('id'))
    ]


def search_uri(
    config: dict[str, Any], artist: str, title: str, *, request=None
) -> Optional[str]:
    """Find a track's Spotify URI by artist + title, or ``None``."""

    current = ensure_token(config, request=request)
    if current is None:
        return None
    query = ' '.join(part for part in (artist, title) if part)
    if not query:
        return None
    sender = request or _request
    try:
        response = sender(
            'GET',
            f'{SPOTIFY_API}/search',
            headers=_bearer(current['access_token']),
            params={'q': query, 'type': 'track', 'limit': 1},
        )
        response.raise_for_status()
        body = response.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning('Spotify search failed for {!r}: {}', query, exc)
        return None
    items = (
        (body or {}).get('tracks', {}).get('items')
        if isinstance(body, dict)
        else []
    )
    if not items:
        return None
    return _text(items[0].get('uri')) or None


def play_track(
    config: dict[str, Any],
    uri: str,
    *,
    device_id: Optional[str] = None,
    silent: bool = True,
    request: Optional[Request] = None,
) -> bool:
    """Start *uri* on the Connect device; ``False`` on any failure.

    *silent* first turns the device's volume to 0 - the user listens in
    Downtify; the mirrored playback is for the record, not the ears.
    """

    current = ensure_token(config, request=request)
    if current is None:
        return False
    target = device_id or current.get('device_id')
    if not target:
        return False
    sender = request or _request
    try:
        if silent:
            sender(
                'PUT',
                f'{SPOTIFY_API}/me/player/volume',
                headers=_bearer(current['access_token']),
                params={'volume_percent': 0, 'device_id': target},
            )
        response = sender(
            'PUT',
            f'{SPOTIFY_API}/me/player/play',
            headers=_bearer(current['access_token']),
            params={'device_id': target},
            json={'uris': [uri]},
        )
        response.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning('Spotify mirror play failed for {}: {}', uri, exc)
        return False


def uri_for_track(
    config: dict[str, Any],
    track: dict[str, Any],
    *,
    library: Any = None,
    request: Optional[Request] = None,
) -> Optional[str]:
    """The Spotify URI for a reported track, or ``None``.

    A downloaded track's id is in the track index (every Downtify
    download registers there); anything else falls back to a Spotify
    search by artist + title.
    """

    if not isinstance(track, dict):
        return None
    if library is not None:
        track_index = getattr(library, 'track_index', None)
        if track_index is not None:
            stored = track_index.spotify_id_for_filename(
                _text(track.get('file'))
            )
            if stored:
                return f'spotify:track:{stored}'
    return search_uri(
        config,
        _text(track.get('artist')),
        _text(track.get('title')),
        request=request,
    )


def mirror_track(
    config: dict[str, Any],
    track: dict[str, Any],
    *,
    library: Any = None,
    request: Optional[Request] = None,
) -> Optional[dict[str, Any]]:
    """Mirror one play; ``None`` when skipped, tokens dict when done.

    The tokens dict is what the caller persists when :func:`ensure_token`
    renewed the access token mid-flight (``{}`` when it wasn't).
    """

    uri = uri_for_track(config, track, library=library, request=request)
    if not uri:
        return None
    if play_track(
        config,
        uri,
        silent=bool(config.get('silent_on_target', True)),
        request=request,
    ):
        current = ensure_token(config, request=request)
        if current and current.get('access_token') != config.get(
            'access_token'
        ):
            return {
                'access_token': current['access_token'],
                'refresh_token': current.get('refresh_token', ''),
                'token_expires_at': current.get('token_expires_at', 0),
            }
    return {}


def verify_connection(
    config: dict[str, Any], *, request: Optional[Request] = None
) -> dict[str, Any]:
    """Check the connect: tokens work and the device is visible.

    ``{ok, username?, device?|error?}``.
    """

    current = ensure_token(config, request=request)
    if current is None:
        return {'ok': False, 'error': 'auth_failed'}
    sender = request or _request
    try:
        response = sender(
            'GET',
            f'{SPOTIFY_API}/me',
            headers=_bearer(current['access_token']),
        )
        response.raise_for_status()
        me = response.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning('Spotify mirror test failed: {}', exc)
        return {'ok': False, 'error': 'auth_failed'}
    username = _text((me or {}).get('display_name')) or _text(
        (me or {}).get('id')
    )
    devices = list_devices(current, request=request)
    target = current.get('device_id')
    device = next((d for d in devices if d['id'] == target), None)
    if device is None:
        return {
            'ok': False,
            'error': 'device_missing',
            'username': username,
        }
    return {
        'ok': True,
        'username': username,
        'device': device['name'],
    }


class MirrorTracker:
    """In-memory: which (player, song) was already mirrored.

    Keeps repeated reports of the same song from one player (heartbeat
    every 30 s, pause/resume) from sending the same play command again.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._mirrored: dict[tuple[int, str], str] = {}

    def should_mirror(self, user_id: int, player: str, song: str) -> bool:
        key = (int(user_id), player)
        with self._lock:
            if self._mirrored.get(key) == song:
                return False
            self._mirrored[key] = song
            return True

    def forget_user(self, user_id: int) -> None:
        with self._lock:
            for key in [k for k in self._mirrored if k[0] == user_id]:
                del self._mirrored[key]
