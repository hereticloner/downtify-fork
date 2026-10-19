"""Live sync of downloaded Spotify playlists with their Spotify source.

A playlist downloaded from Spotify is a snapshot: the day it lands, its
M3U and catalog mirror the playlist as it was then. When tracks are added
or removed on Spotify the local copy drifts until the user re-imports it
by hand. This module keeps the local membership honest.

It reuses the OAuth connection the Spotify Mirror already owns
(``downtify.spotify_mirror``): the same client id and tokens, the same
``ensure_token`` refresh, nothing new to connect. For every playlist the
library knows by Spotify id it fetches the current track list from the
Web API, diffs it against the last snapshot it stored, and applies the
difference - new tracks join the playlist (the missing-tracks download
flow pulls the audio) and removed ones drop out of the playlist's M3U and
catalog. Audio files are never deleted; only the playlist's membership
changes.

The feature is off by default (Settings -> Spotify Sync): nothing is
fetched until the user turns it on. Every failure is logged and reported
back in the returned summary, which is what the loop turns into a toast;
a failed sync never raises into the caller.
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable, Optional

import httpx
from loguru import logger

from . import m3u, spotify_mirror
from .library_paths import locate_library_file
from .library_paths_cache import invalidate_library_paths_cache

#: The settings block this feature reads (see ``api.DEFAULT_SETTINGS``).
SETTINGS_KEY = 'spotify_sync'
DEFAULT_INTERVAL_MINUTES = 60
MIN_INTERVAL_MINUTES = 5
#: A week. A daily-or-longer cadence is the useful range; anything past
#: this is a typo, not a policy.
MAX_INTERVAL_MINUTES = 7 * 24 * 60
_STORE_VERSION = 1

#: Request seam: tests inject a fake; the default is a plain httpx call.
Request = Callable[..., Any]
#: ``(playlist_name, added_ids, removed_ids)`` - how the caller applies a
#: diff to its own stores.
ApplyDiff = Callable[[str, list[str], list[str]], None]

_HTTP_TIMEOUT = spotify_mirror.TIMEOUT_SECONDS


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_settings() -> dict[str, Any]:
    """The stored shape of the ``spotify_sync`` block (off by default)."""

    return {
        'enabled': False,
        'interval_minutes': DEFAULT_INTERVAL_MINUTES,
    }


def clamp_interval_minutes(value: Any) -> int:
    """Coerce and clamp a requested sync interval, in minutes."""

    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return DEFAULT_INTERVAL_MINUTES
    return min(MAX_INTERVAL_MINUTES, max(MIN_INTERVAL_MINUTES, minutes))


def clean_settings(value: Any) -> dict[str, Any]:
    """Coerce a ``spotify_sync`` block to the stored shape."""

    base = default_settings()
    if isinstance(value, dict):
        base.update(value)
    return {
        'enabled': bool(base.get('enabled')),
        'interval_minutes': clamp_interval_minutes(
            base.get('interval_minutes')
        ),
    }


def is_enabled(settings: Any) -> bool:
    """Whether the sync switch is on in a whole settings mapping."""

    block = settings.get(SETTINGS_KEY) if isinstance(settings, dict) else None
    return bool(isinstance(block, dict) and block.get('enabled'))


def interval_minutes(settings: Any) -> int:
    """The configured interval (clamped) from a whole settings mapping."""

    block = settings.get(SETTINGS_KEY) if isinstance(settings, dict) else None
    if isinstance(block, dict):
        return clamp_interval_minutes(block.get('interval_minutes'))
    return DEFAULT_INTERVAL_MINUTES


# ── snapshots ────────────────────────────────────────────────────────


def _track_id(entry: Any) -> str:
    if isinstance(entry, str):
        return entry.strip()
    if isinstance(entry, dict):
        for key in ('song_id', 'id', 'track_id'):
            value = entry.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        uri = entry.get('uri')
        if isinstance(uri, str) and uri.strip():
            return uri.rsplit(':', 1)[-1].strip()
    return ''


def normalize_snapshot(tracks: Any) -> list[str]:
    """Ordered, unique Spotify track ids from track dicts or raw ids.

    Accepts what both Spotify sources hand back - embed/GraphQL song
    dicts (``song_id``), Web API track objects (``id``) or a plain list
    of ids - and always yields the same shape so two snapshots compare.
    """

    if not isinstance(tracks, (list, tuple)):
        return []
    ids: list[str] = []
    seen: set[str] = set()
    for entry in tracks:
        tid = _track_id(entry)
        if tid and tid not in seen:
            seen.add(tid)
            ids.append(tid)
    return ids


def snapshot_diff(previous: Any, current: Any) -> dict[str, Any]:
    """What changed between two snapshots.

    ``added`` are the ids *current* has that *previous* did not (in the
    order Spotify returns them); ``removed`` are the ones *previous* had
    that are gone (in their old order). ``changed`` is True when either
    is non-empty. A pure reorder is deliberately not a change - the local
    membership is a set, and rewriting the M3U for a shuffle would be
    noise.
    """

    prev = normalize_snapshot(previous)
    cur = normalize_snapshot(current)
    prev_set = set(prev)
    cur_set = set(cur)
    added = [tid for tid in cur if tid not in prev_set]
    removed = [tid for tid in prev if tid not in cur_set]
    return {
        'added': added,
        'removed': removed,
        'changed': bool(added or removed),
    }


def _parse_iso(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def is_due(
    last_synced: Any,
    interval_minutes: int,
    *,
    now: Optional[datetime] = None,
) -> bool:
    """Whether a playlist not touched since *last_synced* is due again.

    A missing or malformed stamp counts as due (so a first run or a
    hand-edited store still syncs).
    """

    last = _parse_iso(last_synced)
    if last is None:
        return True
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    due_at = last + timedelta(minutes=clamp_interval_minutes(interval_minutes))
    return current >= due_at


# ── the Spotify snapshot store ───────────────────────────────────────


class SyncSnapshotStore:
    """The last-known Spotify track ids per playlist, in one JSON file.

    Lives next to the other Downtify databases (``/data``), not in the
    downloads volume: it is a cache of what Spotify said last time, not
    library data, and losing it only means one baseline re-fetch.

    Writers serialize on a lock and the file is replaced atomically. Both
    matter: the periodic loop and a manual "Sync now" write the same file,
    and every write is a read-modify-write of the whole map - without the
    lock the slower writer's entries disappear, and a write interrupted
    halfway used to leave JSON that ``_load`` reads as empty, losing every
    baseline at once.
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._lock = threading.RLock()

    def _load(self) -> dict[str, Any]:
        try:
            data = json.loads(self._path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            data = None
        playlists = data.get('playlists') if isinstance(data, dict) else None
        if not isinstance(playlists, dict):
            playlists = {}
        return {'version': _STORE_VERSION, 'playlists': playlists}

    def _write(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(data, ensure_ascii=False, indent=2)
        # Same directory, so os.replace stays atomic on the same filesystem.
        tmp = self._path.with_name(f'{self._path.name}.tmp')
        try:
            with open(tmp, 'w', encoding='utf-8') as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self._path)
        except OSError:
            try:
                tmp.unlink()
            except OSError:
                pass
            raise

    def all(self) -> dict[str, Any]:
        return self._load()['playlists']

    def entry(self, playlist_id: str) -> Optional[dict[str, Any]]:
        sid = str(playlist_id or '').strip()
        if not sid:
            return None
        entry = self._load()['playlists'].get(sid)
        return entry if isinstance(entry, dict) else None

    def track_ids(self, playlist_id: str) -> Optional[list[str]]:
        """The stored snapshot, or ``None`` when there is no baseline yet."""

        entry = self.entry(playlist_id)
        if entry is None:
            return None
        return normalize_snapshot(entry.get('track_ids'))

    def synced_at(self, playlist_id: str) -> Optional[str]:
        entry = self.entry(playlist_id)
        if entry is None:
            return None
        value = entry.get('synced_at')
        return str(value) if isinstance(value, str) and value else None

    def save(
        self,
        playlist_id: str,
        track_ids: Any,
        *,
        name: str = '',
        synced_at: Optional[str] = None,
        snapshot_id: Optional[str] = None,
    ) -> None:
        sid = str(playlist_id or '').strip()
        if not sid:
            return
        with self._lock:
            data = self._load()
            previous = data['playlists'].get(sid)
            # A save without a snapshot (a hand-edited store, a caller
            # that never read the metadata) must not drop the one already
            # stored - the cheap "nothing changed" check compares it.
            if snapshot_id is None and isinstance(previous, dict):
                snapshot_id = previous.get('snapshot_id')
            data['playlists'][sid] = {
                'name': str(name or ''),
                'track_ids': normalize_snapshot(track_ids),
                'synced_at': synced_at or _now_iso(),
                'snapshot_id': str(snapshot_id or ''),
            }
            self._write(data)

    def snapshot_id(self, playlist_id: str) -> Optional[str]:
        """The Spotify ``snapshot_id`` this playlist was last synced at."""

        entry = self.entry(playlist_id)
        if entry is None:
            return None
        value = entry.get('snapshot_id')
        return str(value) if isinstance(value, str) and value else None

    def forget(self, playlist_id: str) -> bool:
        sid = str(playlist_id or '').strip()
        if not sid:
            return False
        with self._lock:
            data = self._load()
            if data['playlists'].pop(sid, None) is None:
                return False
            self._write(data)
        return True


# ── OAuth fetch (the existing Spotify Mirror connection) ─────────────


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
        timeout=_HTTP_TIMEOUT,
    )


class ScopeRequired(Exception):
    """Spotify refused a playlist read because the token lacks the scopes.

    Measured 2026-10-15: a token granted before the playlist scopes were
    added answers 403 - ``/me/playlists`` with
    ``{"message": "Insufficient client scope"}``, every
    ``/playlists/{id}/tracks`` with ``Forbidden``. It is not a rate
    limit: no wait clears it, because a refresh grant cannot add scopes
    the authorization never asked for. The account has to reconnect, so
    the caller must be able to say exactly that.
    """


class RateLimited(Exception):
    """Spotify refused a fetch with 429 and said for how long.

    Carries the ``Retry-After`` in seconds so the caller can both say
    something useful and stop asking.
    """

    def __init__(self, retry_after: int) -> None:
        super().__init__(f'rate limited for {retry_after}s')
        self.retry_after = max(int(retry_after), 1)


#: playlist id -> epoch second until which Spotify asked us to stop asking.
#:
#: A refused fetch never writes ``synced_at``, so the interval check in
#: :func:`run_sync` cannot see it: without this the sweep re-asked every
#: 120 seconds (418 playlist fetches in a day, measured 2026-10-14) and
#: each ask lengthened the penalty it was serving. In-process is enough -
#: a restart costs one extra sweep.
_RATE_LIMITED_UNTIL: dict[str, float] = {}

#: Longest a 429 refusal is believed for, whatever Spotify asks.
#:
#: Measured 2026-10-19 on a live server: the header came back numeric at
#: 40000 s (~11 h) and every one of the four playlists was locked for
#: that whole span, silently - the sweep logged "next try in 660 min"
#: every two minutes and told nobody, so the user reported the automatic
#: sync as broken. The quota is shared and the answer is the server's;
#: nothing here can make an eleven-hour refusal shorter. Four hours is
#: still long enough that the account's access token has been refreshed
#: at least once underneath it, and it is short enough that the feature
#: recovers on its own instead of needing a restart.
MAX_RETRY_AFTER_SECONDS = 4 * 3600


def in_rate_limit_cooldown(playlist_id: str) -> bool:
    """Whether Spotify's refusal for this playlist is still in effect."""

    sid = str(playlist_id or '').strip()
    until = _RATE_LIMITED_UNTIL.get(sid, 0.0)
    if until <= time.time():
        _RATE_LIMITED_UNTIL.pop(sid, None)
        return False
    return True


def rate_limit_retry_after(playlist_id: str) -> int:
    """Seconds left on this playlist's refusal, ``0`` when there is none."""

    return max(
        int(
            _RATE_LIMITED_UNTIL.get(str(playlist_id or '').strip(), 0.0)
            - time.time()
        ),
        0,
    )


def _retry_after_seconds(exc: Exception, default: int = 900) -> int:
    """The ``Retry-After`` header on an HTTP error, in seconds.

    Two shapes are legal (RFC 9110 §10.2.3) and both are seen from
    Spotify: a delay in seconds, and a date. ``int()`` read only the
    first, so a date quietly became ``default``. A date is read as
    ISO-8601 (``Z`` included) or as the HTTP-date the RFC names, and a
    naive one - which is what both spellings look like from a UTC
    server - is taken as UTC, because that is what a Spotify date
    means. A date already in the past falls back to ``default`` rather
    than to "ask immediately".

    The answer is then clamped to :data:`MAX_RETRY_AFTER_SECONDS`: the
    code cannot shorten a real quota refusal, but a refusal it believes
    for half a day outlives everything it was set for and, if it is
    never announced, is indistinguishable from a broken feature. An
    absent or unreadable header is ``default`` (15 minutes).
    """

    response = getattr(exc, 'response', None)
    header = getattr(response, 'headers', {}).get('retry-after')
    text = str(header or '').strip()
    if not text:
        return default
    try:
        seconds = int(text)
    except ValueError:
        when = _retry_after_date(text)
        if when is None:
            return default
        seconds = round((when - datetime.now(timezone.utc)).total_seconds())
        if seconds <= 0:
            return default
    return max(0, min(seconds, MAX_RETRY_AFTER_SECONDS))


def _retry_after_date(text: str) -> Optional[datetime]:
    """A ``Retry-After`` date in UTC, or ``None`` when it is neither shape.

    ISO-8601 is what a JSON API tends to write; the HTTP-date the RFC
    names is what a proxy tends to write. Both end up here.
    """

    try:
        when = datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        try:
            when = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return None
        if when is None:  # raises on junk, but None is not out of the question
            return None
    if when.tzinfo is None:
        return when.replace(tzinfo=timezone.utc)
    return when


def fetch_snapshot_id(
    config: dict[str, Any],
    playlist_id: str,
    *,
    request: Optional[Request] = None,
) -> Optional[str]:
    """The playlist's current ``snapshot_id``, or ``None`` when unavailable.

    The cheap "did anything change?" question. ``GET /playlists/{id}``
    sits outside the playlist-item quota (measured 2026-10-15, it
    answered 200 while every ``/tracks`` page said 429
    ``QUOTA_EXCEEDED``), and it carries the id Spotify rewrites on every
    edit. A caller that gets nothing here simply falls back to reading
    the tracks.
    """

    sid = str(playlist_id or '').strip()
    if not sid:
        return None
    current = spotify_mirror.ensure_token(config, request=request)
    if current is None:
        return None
    # Hand the caller the possible renewal; it owns persistence.
    config['access_token'] = current.get('access_token', '')
    config['refresh_token'] = current.get('refresh_token', '')
    config['token_expires_at'] = current.get('token_expires_at', '')
    sender = request or _request
    try:
        response = sender(
            'GET',
            f'{spotify_mirror.SPOTIFY_API}/playlists/{sid}',
            headers={
                'Authorization': 'Bearer '
                + str(current.get('access_token') or '')
            },
        )
        response.raise_for_status()
        body = response.json()
    except Exception as exc:  # noqa: BLE001 - the caller falls back
        logger.debug('Spotify sync: no snapshot for playlist {}: {}', sid, exc)
        return None
    if not isinstance(body, dict):
        return None
    value = body.get('snapshot_id')
    return str(value) if value else None


def fetch_snapshot(
    config: dict[str, Any],
    playlist_id: str,
    *,
    request: Optional[Request] = None,
) -> Optional[list[str]]:
    """The playlist's current Spotify track ids, or ``None`` on failure.

    Uses the mirror's tokens; a stale access token is renewed through
    ``spotify_mirror.ensure_token`` and the renewed fields are written
    back onto *config* so the caller can persist them. Pages the Web API
    until every track is read. Any failure - no working token, an HTTP
    error, a non-JSON body - is logged and reported as ``None``; a 429
    raises :class:`RateLimited` instead, because it is the one failure
    the caller has to remember.
    """

    sid = str(playlist_id or '').strip()
    if not sid:
        return None
    current = spotify_mirror.ensure_token(config, request=request)
    if current is None:
        logger.warning(
            'Spotify sync: no working token for playlist {} '
            '- reconnect Spotify in Settings',
            sid,
        )
        return None
    # Hand the caller the possible renewal; it owns persistence.
    config['access_token'] = current.get('access_token', '')
    config['refresh_token'] = current.get('refresh_token', '')
    config['token_expires_at'] = current.get('token_expires_at', '')

    sender = request or _request
    token = str(current.get('access_token') or '')
    url = f'{spotify_mirror.SPOTIFY_API}/playlists/{sid}/tracks'
    params: Optional[dict[str, Any]] = {'limit': 100, 'offset': 0}
    ids: list[str] = []
    try:
        while url:
            response = sender(
                'GET',
                url,
                headers={'Authorization': f'Bearer {token}'},
                params=params,
            )
            response.raise_for_status()
            body = response.json()
            items = body.get('items') if isinstance(body, dict) else None
            for item in items or []:
                if not isinstance(item, dict):
                    continue
                # The endpoint wraps each row as ``track``; newer Web API
                # responses use ``item``. Accept both so a shape change
                # doesn't silently read nothing.
                track = item.get('track') or item.get('item')
                tid = _track_id(track)
                if tid:
                    ids.append(tid)
            url = body.get('next') if isinstance(body, dict) else ''
            params = None
    except Exception as exc:  # noqa: BLE001 - reported to the user, not raised
        status = getattr(getattr(exc, 'response', None), 'status_code', None)
        if status == 429:
            limited = RateLimited(_retry_after_seconds(exc))
            _RATE_LIMITED_UNTIL[sid] = time.time() + limited.retry_after
            # Say so when the clamp bit: the number below is ours, not
            # Spotify's, and an operator comparing the two needs to know.
            capped = (
                ' (capped, Spotify asked for longer)'
                if limited.retry_after >= MAX_RETRY_AFTER_SECONDS
                else ''
            )
            logger.warning(
                'Spotify sync: playlist {} refused (429), next try in {} min{}',
                sid,
                round(limited.retry_after / 60),
                capped,
            )
            raise limited from exc
        if status in {401, 403}:
            # 403 = the playlist scopes are missing on this token; 401 =
            # a token Spotify no longer accepts. Neither is retryable.
            logger.warning(
                'Spotify sync: playlist {} refused ({}): the connection '
                'has no permission for playlist reads - reconnect Spotify '
                'in Settings',
                sid,
                status,
            )
            raise ScopeRequired(str(status)) from exc
        logger.warning('Spotify sync: playlist {} fetch failed: {}', sid, exc)
        return None
    return ids


# ── applying a diff to the local playlist ────────────────────────────


def _removed_abs_paths(
    rows: list[dict[str, Any]],
    removed_ids: set[str],
    download_dir: Path,
    slskd_dir: Optional[Path],
    extra_dirs: Any,
) -> set[Path]:
    """The on-disk paths of the removed rows, for filtering the M3U."""

    removed_abs: set[Path] = set()
    for row in rows:
        tid = str(row.get('track_spotify_id') or '').strip()
        if tid not in removed_ids:
            continue
        filename = str(row.get('filename') or '').strip()
        if not filename:
            continue
        path = locate_library_file(
            filename, download_dir, slskd_dir, extra_dirs
        )
        if path is not None:
            removed_abs.add(Path(path).resolve())
    return removed_abs


def _strip_m3u_tracks(m3u_path: Path, removed_abs: set[Path]) -> bool:
    """Drop the removed tracks' lines (and their ``#EXTINF``) from an M3U.

    Filtering the file rather than regenerating it keeps every kept
    track's own title/artist/duration line intact. Returns whether the
    file existed and was rewritten.
    """

    try:
        text = m3u_path.read_text(encoding='utf-8')
    except OSError:
        return False
    m3u_dir = m3u_path.resolve().parent
    out: list[str] = []
    pending: Optional[str] = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            out.append(line)
            continue
        if stripped.startswith('#'):
            if stripped.upper().startswith('#EXTINF'):
                pending = line
            else:
                out.append(line)
            continue
        try:
            resolved: Optional[Path] = (m3u_dir / stripped).resolve()
        except OSError:
            resolved = None
        if resolved is not None and resolved in removed_abs:
            # Drop the track and the label that introduced it.
            pending = None
            continue
        if pending is not None:
            out.append(pending)
            pending = None
        out.append(line)
    if pending is not None:
        out.append(pending)
    m3u_path.write_text('\n'.join(out) + '\n', encoding='utf-8')
    return True


def apply_removals(
    catalog: Any,
    download_dir: Path,
    playlist_name: str,
    removed: list[str],
    *,
    playlist_subdir: Optional[str] = None,
    slskd_dir: Optional[Path] = None,
    extra_dirs: Any = None,
) -> int:
    """Drop *removed* tracks from a playlist's catalog rows and its M3U.

    Only the playlist's membership changes: the catalog rows for the
    tracks go away and their lines are filtered out of the M3U, so the
    playlist stops listing them. The audio files stay on disk (a song
    can belong to other playlists, and deleting audio is never the
    sync's call). Returns how many catalog rows were removed.
    """

    name = str(playlist_name or '').strip()
    wanted = {str(tid).strip() for tid in removed or [] if str(tid).strip()}
    if catalog is None or not name or not wanted:
        return 0
    download_dir = Path(download_dir)
    rows = catalog.list_tracks(name)
    removed_abs = _removed_abs_paths(
        rows, wanted, download_dir, slskd_dir, extra_dirs
    )
    dropped = 0
    for tid in wanted:
        if catalog.remove_track(name, tid):
            dropped += 1
    if dropped == 0:
        return 0
    if removed_abs:
        _strip_m3u_tracks(
            m3u.m3u_path_for(
                download_dir, name, playlist_subdir=playlist_subdir
            ),
            removed_abs,
        )
    invalidate_library_paths_cache()
    return dropped


# ── the sync pass ────────────────────────────────────────────────────


def sync_playlist(
    playlist: dict[str, Any],
    *,
    config: dict[str, Any],
    store: SyncSnapshotStore,
    apply: ApplyDiff,
    request: Optional[Request] = None,
) -> dict[str, Any]:
    """Sync one playlist; never raises.

    Returns ``{playlist_id, name, added, removed, changed, first_run,
    error}``. The first ever sync records a baseline and applies nothing
    - otherwise every existing track would read as "added". When Spotify's
    ``snapshot_id`` still matches the stored one nothing is read at all
    (``skipped='unchanged'``); when it matches but the tracks don't, *apply*
    is not called and the stored timestamp is refreshed.
    ``error='rate_limited'`` carries ``retry_after`` seconds;
    ``error='scope_missing'`` means Spotify refused the playlist read
    because the connection has no playlist permission - reconnect Spotify
    in Settings, because no retry can clear it.
    """

    sid = str(playlist.get('spotify_id') or '').strip()
    name = str(playlist.get('name') or sid)
    result: dict[str, Any] = {
        'playlist_id': sid,
        'name': name,
        'added': [],
        'removed': [],
        'changed': False,
        'first_run': False,
        'error': '',
        'skipped': '',
    }
    if not sid:
        result['error'] = 'no_playlist_id'
        return result

    # Cheap check first: the playlist's own metadata says whether Spotify
    # changed anything at all, and it is not on the quota that
    # /playlists/{id}/tracks is. Only a changed (or unknown) snapshot
    # costs a full read.
    snapshot_id = fetch_snapshot_id(config, sid, request=request)
    known = store.snapshot_id(sid)
    if snapshot_id and known and snapshot_id == known:
        result['skipped'] = 'unchanged'
        store.save(
            sid, store.track_ids(sid), name=name, snapshot_id=snapshot_id
        )
        return result

    try:
        current = fetch_snapshot(config, sid, request=request)
    except RateLimited as limited:
        result['error'] = 'rate_limited'
        result['retry_after'] = limited.retry_after
        return result
    except ScopeRequired:
        result['error'] = 'scope_missing'
        return result
    if current is None:
        result['error'] = 'auth_failed'
        return result

    previous = store.track_ids(sid)
    if previous is None:
        # First look: the local copy is the baseline, not a pile of
        # additions.
        result['first_run'] = True
        store.save(sid, current, name=name, snapshot_id=snapshot_id)
        return result

    diff = snapshot_diff(previous, current)
    if not diff['changed']:
        store.save(sid, current, name=name, snapshot_id=snapshot_id)
        return result

    result['added'] = list(diff['added'])
    result['removed'] = list(diff['removed'])
    result['changed'] = True
    try:
        apply(name, diff['added'], diff['removed'])
    except Exception:  # noqa: BLE001 - reported, never raised
        logger.exception(
            'Spotify sync: applying changes for playlist {!r} failed', name
        )
        result['error'] = 'apply_failed'
        return result
    store.save(sid, current, name=name, snapshot_id=snapshot_id)
    logger.info(
        'Spotify sync: {!r} +{} -{} track(s)',
        name,
        len(diff['added']),
        len(diff['removed']),
    )
    return result


def run_sync(
    playlists: list[dict[str, Any]],
    *,
    settings: dict[str, Any],
    store: SyncSnapshotStore,
    apply: ApplyDiff,
    credentials: Optional[dict[str, Any]] = None,
    request: Optional[Request] = None,
    force: bool = False,
) -> dict[str, Any]:
    """Sync every known playlist; a no-op while the feature is off.

    A playlist is skipped when it was synced less than the configured
    interval ago, unless *force* (the manual "Sync now" button) - which
    also lets that button run while the switch is still off, and also
    ignores a live rate-limit cooldown, because that button is the user
    asking again on purpose. The returned summary carries the per-playlist
    results, aggregate counts and, when the token was renewed mid-run, the
    fields to persist under ``tokens``. ``rate_limited`` /
    ``retry_after_minutes`` say that Spotify refused and for how long;
    ``scope_missing`` counts playlists the connection has no permission
    to read (a reconnect fixes those, so it is reported apart).
    """

    block = clean_settings(settings.get(SETTINGS_KEY))
    summary: dict[str, Any] = {
        'enabled': block['enabled'],
        'interval_minutes': block['interval_minutes'],
        'playlists': [],
        'added': 0,
        'removed': 0,
        'changed': 0,
        'errors': 0,
        'skipped': 0,
        'error': '',
        'rate_limited': 0,
        'retry_after_minutes': 0,
        'scope_missing': 0,
    }
    if not block['enabled'] and not force:
        return summary
    if not isinstance(credentials, dict) or not credentials.get('client_id'):
        summary['error'] = 'not_connected'
        summary['errors'] = len(playlists)
        summary['playlists'] = [
            {
                'playlist_id': str(p.get('spotify_id') or ''),
                'name': str(p.get('name') or ''),
                'error': 'not_connected',
            }
            for p in playlists
        ]
        return summary

    config = dict(credentials)
    before_token = config.get('access_token')
    interval = block['interval_minutes']
    for playlist in playlists:
        sid = str(playlist.get('spotify_id') or '').strip()
        if not force and sid and in_rate_limit_cooldown(sid):
            summary['skipped'] += 1
            summary['rate_limited'] += 1
            summary['retry_after_minutes'] = max(
                summary['retry_after_minutes'],
                round(rate_limit_retry_after(sid) / 60),
            )
            continue
        if not force and sid and not is_due(store.synced_at(sid), interval):
            summary['skipped'] += 1
            continue
        result = sync_playlist(
            playlist,
            config=config,
            store=store,
            apply=apply,
            request=request,
        )
        summary['playlists'].append(result)
        summary['added'] += len(result['added'])
        summary['removed'] += len(result['removed'])
        summary['changed'] += 1 if result['changed'] else 0
        summary['errors'] += 1 if result['error'] else 0
        summary['skipped'] += 1 if result.get('skipped') else 0
        if result['error'] == 'rate_limited':
            summary['rate_limited'] += 1
            summary['retry_after_minutes'] = max(
                summary['retry_after_minutes'],
                round(int(result.get('retry_after') or 0) / 60),
            )
        elif result['error'] == 'scope_missing':
            summary['scope_missing'] += 1
    if config.get('access_token') != before_token and config.get('client_id'):
        summary['tokens'] = {
            'access_token': config.get('access_token', ''),
            'refresh_token': config.get('refresh_token', ''),
            'token_expires_at': config.get('token_expires_at', ''),
        }
    return summary


# ── the periodic sweep ───────────────────────────────────────────────


async def spotify_sync_loop(
    *,
    get_settings: Callable[[], Any],
    get_playlists: Callable[[], list[dict[str, Any]]],
    get_credentials: Callable[[], Optional[dict[str, Any]]],
    get_store: Callable[[], Optional[SyncSnapshotStore]],
    apply: ApplyDiff,
    broadcast: Optional[Callable[[dict[str, Any]], Any]] = None,
    idle_seconds: float = 120.0,
) -> None:
    """Background task: run a due-only sweep while the switch is on.

    Idles cheaply: with the feature off (the default) or its store
    missing it never touches Spotify. Errors are logged and - when a
    *broadcast* sink is given - announced as a ``spotify_sync`` event so
    the open page can show a toast; the loop itself never dies.
    """

    while True:
        try:
            settings = get_settings()
            store = get_store()
            if is_enabled(settings) and store is not None:
                summary = await asyncio.to_thread(
                    run_sync,
                    get_playlists(),
                    settings=settings,
                    store=store,
                    apply=apply,
                    credentials=get_credentials(),
                )
                if summary.get('changed'):
                    logger.info(
                        'Spotify sync: +{} -{} track(s)',
                        summary.get('added', 0),
                        summary.get('removed', 0),
                    )
                if summary.get('rate_limited'):
                    logger.warning(
                        'Spotify rate limited: {} playlist(s), next try in '
                        '{} min',
                        summary['rate_limited'],
                        summary.get('retry_after_minutes', 0),
                    )
                elif summary.get('scope_missing'):
                    logger.warning(
                        'Spotify sync: {} playlist(s) unreadable - the '
                        'connection has no playlist permission, reconnect '
                        'Spotify in Settings',
                        summary['scope_missing'],
                    )
                elif summary.get('errors'):
                    logger.warning(
                        'Spotify sync finished with {} error(s)',
                        summary['errors'],
                    )
                # An unattached account is a standing state, not an event:
                # it is shown in Settings, not re-toasted every wake-up.
                # A token that needs reconnecting is the same - the fix is
                # a click in Settings, not another failed sweep. A rate
                # limit is neither: it is silent everywhere else, and
                # measured 2026-10-19 a four-hour-long one was reported as
                # "the automatic sync stopped working" because nothing
                # said so. It rides the same event and the browser shows
                # it once per cooldown rather than once per wake-up.
                notify = (
                    summary.get('changed')
                    or bool(summary.get('rate_limited'))
                    or (
                        summary.get('errors')
                        and summary.get('error') != 'not_connected'
                        and not summary.get('scope_missing')
                    )
                )
                if broadcast is not None and notify:
                    await broadcast({'type': 'spotify_sync', **summary})
        except Exception:  # noqa: BLE001 - a loop must survive everything
            logger.exception('Spotify sync loop failed')
        await asyncio.sleep(idle_seconds)
