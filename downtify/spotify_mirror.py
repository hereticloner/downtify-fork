"""Mirror plays to Spotify Connect: Downtify listening shows up on
Spotify - "Recently played", Friend Activity, the year wrap-up.

Spotify only records real playback; nothing can inject listening
history (and the private endpoints that try are an account-ban risk).
What the documented Web API can do is ask the user's own Premium
account to play the same track on a Spotify Connect device. This fork
ships one on the server: the "Downtify Mirror" spotifyd container,
silent (volume 0) and always online. A play in Downtify starts the same
song there, and Spotify counts it like any other playback.

The play is always a bare track, never a playlist ``context_uri``: a
context makes the Connect device walk that playlist, and a track it
cannot load makes it skip to the next one, so the account raced through
the playlist a second at a time (measured 2026-10-14) and none of it
counted as listening. What the mirror needs is that the track plays
long enough to be a real listen.

Only a track's START is mirrored - the same ``started`` signal
scrobbling uses - deduped per player and song, so a scrub or a
pause/resume doesn't spam the API. Everything is best-effort: a mirror
failure is logged and dropped, never raised, and never touches the
playback that triggered it.

OAuth is Authorization Code + PKCE (no client secret needed): the user
creates their own Spotify app, points its redirect URI at this server,
connects in Settings → Spotify Mirror, and the tokens are stored in the
``spotify_mirror`` settings block. Scopes are playback ones, plus the two
playlist-read ones the live sync (``downtify.spotify_sync``) reuses the
same connection for: ``user-read-playback-state``,
``user-modify-playback-state``, ``user-read-currently-playing``,
``playlist-read-private``, ``playlist-read-collaborative``.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import threading
import time
from dataclasses import dataclass, field, replace
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
    'user-read-currently-playing playlist-read-private '
    'playlist-read-collaborative user-read-recently-played '
    'user-top-read'
)
#: Diagnostics only (:class:`MirrorTracker`): how many ``(user, player)``
#: pairs keep a last success and a last failure. They are a status
#: snapshot, not a history - a long-lived process drops the oldest
#: entries instead of growing with it, and a restart starts empty.
DIAGNOSTIC_LIMIT = 512
ERROR_LIMIT = 256
#: How much of an exception text a diagnostic error reason keeps.
REASON_LIMIT = 160

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


@dataclass(frozen=True)
class MirrorOutcome:
    """What one mirror attempt did, and which step refused it.

    The boolean functions below (``ensure_token``, ``play_track``,
    ``mirror_track``) tell a caller *that* something failed and nothing
    about *why* - the reason ended up in the log and nowhere else, so a
    user whose plays silently never reached Spotify had no way to find
    out. This carries the verdict (``ok``), the reason when there isn't
    one (``error``: ``auth_failed``, ``no_device``, ``no_uri`` or
    ``play_failed: ...``) and the Spotify URI that went out, so a
    caller can show it or record it.
    """

    error: str = ''
    uri: str = ''
    tokens: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.error


def _reason(prefix: str, exc: Exception) -> str:
    """A short, loggable ``<prefix>: <what went wrong>`` for *exc*."""

    return f'{prefix}: {_text(str(exc))[:REASON_LIMIT]}'


def ensure_token_outcome(
    config: dict[str, Any], *, request: Optional[Request] = None
) -> MirrorOutcome:
    """:func:`ensure_token`'s answer, with the reason it failed.

    ``tokens`` is the config to send requests with (the caller's own
    when it is still fresh, a renewed one otherwise); ``error`` is
    ``auth_failed`` when no usable token could be produced.
    """

    expires_at = float(config.get('token_expires_at') or 0)
    fresh = (
        config.get('access_token')
        and expires_at - TOKEN_REFRESH_MARGIN > time.time()
    )
    if fresh:
        return MirrorOutcome(tokens=config)
    renewed = refresh_access_token(
        config['client_id'], config.get('refresh_token', ''), request=request
    )
    if not renewed:
        return MirrorOutcome(error='auth_failed')
    return MirrorOutcome(tokens={**config, **renewed})


def ensure_token(
    config: dict[str, Any], *, request: Optional[Request] = None
) -> Optional[dict[str, Any]]:
    """A config with a fresh access token, refreshing when stale.

    Returns ``None`` when nothing works - use
    :func:`ensure_token_outcome` when the caller has to say why. A
    refreshed token is returned with the new fields - the caller
    persists it in settings.
    """

    return ensure_token_outcome(config, request=request).tokens or None


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


def play_body(uri: str):
    """The ``PUT /me/player/play`` body for *uri*.

    A bare track list, never a ``context_uri``. A playlist context makes
    the Connect device walk that playlist, and a track it cannot load
    (a refused audio key) makes it *skip to the next one* - so Spotify
    raced through the playlist a second at a time while Downtify played
    its own track (measured 2026-10-14). What the mirror needs is that
    the track plays long enough to count as a real listen, not what
    playlist Spotify names it under.
    """

    return {'uris': [uri]}


def play_track_outcome(
    config: dict[str, Any],
    uri: str,
    *,
    device_id: Optional[str] = None,
    silent: bool = True,
    request: Optional[Request] = None,
) -> MirrorOutcome:
    """Start *uri*, reporting which step refused it.

    Same work as :func:`play_track`; the outcome names the reason, so
    a caller can record or surface it instead of dropping a bare
    ``False``. ``auth_failed`` means no usable token, ``no_device``
    that the account has no Connect device to play on, and
    ``play_failed: ...`` carries Spotify's own refusal.
    """

    token = ensure_token_outcome(config, request=request)
    if not token.ok:
        return token
    current = token.tokens
    target = device_id or current.get('device_id')
    if not target:
        return MirrorOutcome(error='no_device', uri=uri)
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
            json=play_body(uri),
        )
        response.raise_for_status()
        return MirrorOutcome(uri=uri)
    except Exception as exc:  # noqa: BLE001
        logger.warning('Spotify mirror play failed for {}: {}', uri, exc)
        return MirrorOutcome(error=_reason('play_failed', exc), uri=uri)


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
    :func:`play_track_outcome` is this with the reason attached.
    """

    return play_track_outcome(
        config,
        uri,
        device_id=device_id,
        silent=silent,
        request=request,
    ).ok


def _transport(
    config: dict[str, Any],
    action: str,
    *,
    params: Optional[dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> bool:
    """One player command (``pause``, ``seek``, resume ``play``)."""

    current = ensure_token(config, request=request)
    if current is None:
        return False
    target = current.get('device_id')
    if not target:
        return False
    sender = request or _request
    query = {'device_id': target, **(params or {})}
    try:
        response = sender(
            'PUT',
            f'{SPOTIFY_API}/me/player/{action}',
            headers=_bearer(current['access_token']),
            params=query,
        )
        response.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning('Spotify mirror {} failed: {}', action, exc)
        return False


def pause_playback(
    config: dict[str, Any], *, request: Optional[Request] = None
) -> bool:
    """Pause the mirrored device (a pause in Downtify)."""

    return _transport(config, 'pause', request=request)


def resume_playback(
    config: dict[str, Any], *, request: Optional[Request] = None
) -> bool:
    """Resume the mirrored device where it stood."""

    return _transport(config, 'play', request=request)


def seek_playback(
    config: dict[str, Any],
    position_seconds: Any,
    *,
    request: Optional[Request] = None,
) -> bool:
    """Move the mirrored device to *position_seconds*."""

    try:
        position_ms = max(0, int(float(position_seconds or 0) * 1000))
    except (TypeError, ValueError):
        return False
    return _transport(
        config, 'seek', params={'position_ms': position_ms}, request=request
    )


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


def mirror_track_outcome(
    config: dict[str, Any],
    track: dict[str, Any],
    *,
    library: Any = None,
    request: Optional[Request] = None,
) -> MirrorOutcome:
    """Mirror one play, reporting which step refused it.

    ``error`` is ``no_uri`` when the track could not be resolved on
    Spotify (nothing was sent), then whatever :func:`play_track_outcome`
    refused with.
    """

    uri = uri_for_track(config, track, library=library, request=request)
    if not uri:
        return MirrorOutcome(error='no_uri')
    outcome = play_track_outcome(
        config,
        uri,
        silent=bool(config.get('silent_on_target', True)),
        request=request,
    )
    if not outcome.ok:
        return outcome
    current = ensure_token(config, request=request)
    if current and current.get('access_token') != config.get('access_token'):
        return replace(
            outcome,
            tokens={
                'access_token': current['access_token'],
                'refresh_token': current.get('refresh_token', ''),
                'token_expires_at': current.get('token_expires_at', 0),
            },
        )
    return outcome


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

    ``None`` means the track could not be resolved on Spotify; a play
    Spotify refused comes back as ``{}``, like any other done attempt -
    callers that need to tell those apart, or to report *why* a play
    didn't happen, want :func:`mirror_track_outcome`.
    """

    outcome = mirror_track_outcome(
        config,
        track,
        library=library,
        request=request,
    )
    if outcome.error == 'no_uri':
        return None
    return outcome.tokens


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


def is_track_end(track: Any, position: Any) -> bool:
    """Whether a report is the track *finishing*, not the user pausing.

    When a track ends the player sends a ``paused`` report whose position
    sits at (or past) the duration. Mirroring that pause parks the
    device at the end and fights the next track's play, so the caller
    skips it. A real pause in the last two seconds is sacrificed.
    """

    if not isinstance(track, dict):
        return False
    try:
        duration = float(track.get('duration') or 0)
        played = float(position or 0)
    except (TypeError, ValueError):
        return False
    return duration > 0 and played >= duration - 2


class MirrorTracker:
    """In-memory: which (player, song) was already mirrored.

    Keeps repeated reports of the same song from one player (heartbeat
    every 30 s, pause/resume) from sending the same play command again.
    Also remembers whether the mirrored song is paused, so a pause in
    Downtify pauses the mirror once and a resume resumes it once.

    The dedupe is a *claim* :meth:`should_mirror` takes before the
    network work; only a play that reached Spotify should keep it, so a
    failed attempt releases it again (:meth:`unmark_attempted`) and the
    next report retries instead of skipping that song for the rest of
    the process' life. What each player last managed is kept alongside,
    for ``GET /api/spotify-mirror/status`` - diagnostics only, bounded
    (:data:`DIAGNOSTIC_LIMIT`, :data:`ERROR_LIMIT`) and gone on restart.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._mirrored: dict[tuple[int, str], str] = {}
        self._paused: dict[tuple[int, str], bool] = {}
        self._last_success: dict[tuple[int, str], dict[str, Any]] = {}
        self._last_error: dict[tuple[int, str], dict[str, Any]] = {}

    @staticmethod
    def _remember(
        store: dict[tuple[int, str], dict[str, Any]],
        key: tuple[int, str],
        entry: dict[str, Any],
        limit: int,
    ) -> None:
        """Keep *entry* under *key*, dropping the oldest past *limit*."""

        store.pop(key, None)
        store[key] = entry
        while len(store) > limit:
            del store[next(iter(store))]

    def should_mirror(self, user_id: int, player: str, song: str) -> bool:
        key = (int(user_id), player)
        with self._lock:
            if self._mirrored.get(key) == song:
                return False
            self._mirrored[key] = song
            self._paused[key] = False
            return True

    def unmark_attempted(self, user_id: int, player: str, song: str) -> bool:
        """Give back the claim :meth:`should_mirror` took, to retry.

        Called after a mirror attempt that never reached Spotify (no URI
        found, tokens that would not renew, the play refused): the song
        is still unmirrored, so the next report from this player should
        try again rather than be deduped away forever. ``False`` when
        the claim already moved on to another song, which must not be
        undone.
        """

        key = (int(user_id), player)
        with self._lock:
            if self._mirrored.get(key) != song:
                return False
            del self._mirrored[key]
            self._paused.pop(key, None)
            return True

    def knows(self, user_id: int, player: str, song: str) -> bool:
        """Whether *song* is the one this player last mirrored."""

        with self._lock:
            return self._mirrored.get((int(user_id), player)) == song

    def should_pause(self, user_id: int, player: str, song: str) -> bool:
        key = (int(user_id), player)
        with self._lock:
            if self._mirrored.get(key) != song:
                return False
            if self._paused.get(key):
                return False
            self._paused[key] = True
            return True

    def should_resume(self, user_id: int, player: str, song: str) -> bool:
        key = (int(user_id), player)
        with self._lock:
            if self._mirrored.get(key) != song:
                return False
            if not self._paused.get(key):
                return False
            self._paused[key] = False
            return True

    def should_pause_any(self, user_id: int, player: str) -> bool:
        """A player that stopped: pause the mirror, once."""

        key = (int(user_id), player)
        with self._lock:
            if key not in self._mirrored or self._paused.get(key):
                return False
            self._paused[key] = True
            return True

    def forget_user(self, user_id: int) -> None:
        with self._lock:
            for store in (
                self._mirrored,
                self._paused,
                self._last_success,
                self._last_error,
            ):
                for key in [k for k in store if k[0] == user_id]:
                    del store[key]

    # -- diagnostics ---------------------------------------------------

    def mark_success(
        self, user_id: int, player: str, uri: str, at: float
    ) -> None:
        """Remember the last play this player got onto the device."""

        self._remember(
            self._last_success,
            (int(user_id), player),
            {'uri': _text(uri), 'at': float(at)},
            DIAGNOSTIC_LIMIT,
        )

    def mark_error(
        self, user_id: int, player: str, reason: str, at: float
    ) -> None:
        """Remember why this player's last mirror attempt failed."""

        self._remember(
            self._last_error,
            (int(user_id), player),
            {'reason': _text(reason), 'at': float(at)},
            ERROR_LIMIT,
        )

    def last_mirror(self, user_id: int, player: str) -> dict[str, Any]:
        """The last successful mirror for this player, ``{}`` if none."""

        with self._lock:
            entry = self._last_success.get((int(user_id), player))
            return dict(entry) if entry else {}

    def last_error(self, user_id: int, player: str) -> dict[str, Any]:
        """The last failure for this player, ``{}`` if none."""

        with self._lock:
            entry = self._last_error.get((int(user_id), player))
            return dict(entry) if entry else {}

    def diagnostics(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Every recorded outcome, keyed ``"<user_id>:<player>"``.

        String keys so an endpoint can hand the two maps straight to a
        JSON response (a tuple key isn't one).
        """

        with self._lock:
            return {
                'last_mirrors': {
                    f'{user_id}:{player}': dict(entry)
                    for (user_id, player), entry in self._last_success.items()
                },
                'last_errors': {
                    f'{user_id}:{player}': dict(entry)
                    for (user_id, player), entry in self._last_error.items()
                },
            }
