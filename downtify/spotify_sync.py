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
from datetime import datetime, timedelta, timezone
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
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

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
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

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
    ) -> None:
        sid = str(playlist_id or '').strip()
        if not sid:
            return
        data = self._load()
        data['playlists'][sid] = {
            'name': str(name or ''),
            'track_ids': normalize_snapshot(track_ids),
            'synced_at': synced_at or _now_iso(),
        }
        self._write(data)

    def forget(self, playlist_id: str) -> bool:
        sid = str(playlist_id or '').strip()
        if not sid:
            return False
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
    error, a non-JSON body - is logged and reported as ``None``.
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
    - otherwise every existing track would read as "added". When nothing
    changed, *apply* is not called at all and the stored timestamp is
    refreshed.
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
    }
    if not sid:
        result['error'] = 'no_playlist_id'
        return result

    current = fetch_snapshot(config, sid, request=request)
    if current is None:
        result['error'] = 'auth_failed'
        return result

    previous = store.track_ids(sid)
    if previous is None:
        # First look: the local copy is the baseline, not a pile of
        # additions.
        result['first_run'] = True
        store.save(sid, current, name=name)
        return result

    diff = snapshot_diff(previous, current)
    if not diff['changed']:
        store.save(sid, current, name=name)
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
    store.save(sid, current, name=name)
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
    also lets that button run while the switch is still off. The
    returned summary carries the per-playlist results, aggregate counts
    and, when the token was renewed mid-run, the fields to persist under
    ``tokens``.
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
                if summary.get('errors'):
                    logger.warning(
                        'Spotify sync finished with {} error(s)',
                        summary['errors'],
                    )
                # An unattached account is a standing state, not an event:
                # it is shown in Settings, not re-toasted every wake-up.
                notify = summary.get('changed') or (
                    summary.get('errors')
                    and summary.get('error') != 'not_connected'
                )
                if broadcast is not None and notify:
                    await broadcast({'type': 'spotify_sync', **summary})
        except Exception:  # noqa: BLE001 - a loop must survive everything
            logger.exception('Spotify sync loop failed')
        await asyncio.sleep(idle_seconds)
