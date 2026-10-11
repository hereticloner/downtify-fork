"""FastAPI router for Spotify live sync (downtify.spotify_sync).

Kept as its own module so upstream merges into ``api.py`` never touch it.
The settings block (``spotify_sync``) lives in ``api.DEFAULT_SETTINGS``;
this module only exposes the status and the manual "Sync now" trigger.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from . import spotify_mirror, spotify_sync
from .errors import ApiError
from .library_paths import slskd_dir_from_downloader

router = APIRouter()


def _state() -> Any:
    from downtify import api as api_mod  # noqa: PLC0415

    return api_mod.state


def _download_dir() -> Path:
    from main import DOWNLOAD_DIR  # noqa: PLC0415

    return Path(DOWNLOAD_DIR)


def sync_credentials() -> dict[str, Any]:
    """The Mirror's OAuth credentials - the flow sync reuses."""

    block = _state().settings.get('spotify_mirror')
    return spotify_mirror.mirror_credentials(block) or {}


def sync_playlists() -> list[dict[str, Any]]:
    """Every local playlist that has a Spotify id behind it.

    The library catalog is the primary source; a playlist still being
    watched (downloaded but not yet catalogued) is included too so a
    brand-new playlist syncs on its first sweep. De-duplicated by id,
    preferring the catalog's name.
    """

    from downtify import api as api_mod  # noqa: PLC0415

    out: dict[str, dict[str, Any]] = {}
    catalog = api_mod.state.playlist_catalog
    if catalog is not None:
        for row in catalog.list_playlists_with_spotify_id():
            sid = str(row.get('spotify_id') or '').strip()
            if sid:
                out[sid] = {
                    'spotify_id': sid,
                    'name': str(row.get('name') or sid),
                    'track_count': int(row.get('track_count') or 0),
                }
    monitor_db = api_mod.state.monitor_db
    if monitor_db is not None:
        for watch in monitor_db.list_playlists():
            if getattr(watch, 'kind', '') != 'playlist':
                continue
            sid = str(getattr(watch, 'spotify_id', '') or '').strip()
            name = str(getattr(watch, 'name', '') or sid)
            if sid and sid not in out:
                out[sid] = {
                    'spotify_id': sid,
                    'name': name,
                    'track_count': 0,
                }
    return list(out.values())


def apply_sync_diff(
    playlist_name: str, added: list[str], removed: list[str]
) -> None:
    """Apply a diff to the local playlist: removals leave, adds stay.

    Additions need no local write - the refreshed Spotify source makes
    the missing-tracks flow pull them, and the catalog gains their rows
    when they land. Removals drop the tracks from the catalog and the
    M3U (see :func:`spotify_sync.apply_removals`); audio is untouched.
    """

    del added
    from downtify import api as api_mod  # noqa: PLC0415
    from downtify import m3u as m3u_mod  # noqa: PLC0415

    downloader = api_mod.state.downloader
    # Same placement rule as the monitor's M3U rewrite: with per-artist/
    # album folders the M3U lives in the legacy Playlists/ directory,
    # otherwise beside the playlist's own folder.
    organize = bool(
        getattr(downloader, 'organize_by_artist', False)
        or getattr(downloader, 'organize_by_album', False)
    )
    subdir = (
        None if organize else m3u_mod.sanitize_playlist_name(playlist_name)
    )
    spotify_sync.apply_removals(
        api_mod.state.playlist_catalog,
        _download_dir(),
        playlist_name,
        removed,
        playlist_subdir=subdir,
        slskd_dir=slskd_dir_from_downloader(downloader),
    )


def _persist_tokens(summary: dict[str, Any]) -> None:
    """Save a token the sweep renewed, then drop it from the response."""

    tokens = summary.pop('tokens', None)
    if not isinstance(tokens, dict) or not tokens:
        return
    from downtify import api as api_mod  # noqa: PLC0415

    api_mod._persist_mirror_tokens(tokens)


def _status() -> dict[str, Any]:
    block = spotify_sync.clean_settings(
        _state().settings.get(spotify_sync.SETTINGS_KEY)
    )
    store = _state().playlist_sync_store
    credentials = sync_credentials()
    connected = bool(
        credentials.get('access_token') or credentials.get('refresh_token')
    )
    playlists: list[dict[str, Any]] = []
    for row in sync_playlists():
        sid = row['spotify_id']
        known = store.track_ids(sid) if store is not None else None
        playlists.append({
            'name': row['name'],
            'spotify_id': sid,
            'track_count': row.get('track_count', 0),
            'known_tracks': len(known) if known is not None else 0,
            'synced_at': store.synced_at(sid) if store is not None else None,
        })
    last_synced = max(
        (p['synced_at'] for p in playlists if p['synced_at']),
        default=None,
    )
    return {
        'enabled': block['enabled'],
        'interval_minutes': block['interval_minutes'],
        'connected': connected,
        'playlist_count': len(playlists),
        'playlists': playlists,
        'last_synced': last_synced,
    }


@router.get('/api/spotify-sync')
async def spotify_sync_status_endpoint() -> dict[str, Any]:
    """The sync switch, its interval, and each playlist's last snapshot."""

    return _status()


@router.post('/api/spotify-sync/run')
async def spotify_sync_run_endpoint() -> dict[str, Any]:
    """Sync every playlist now, ignoring the interval.

    Works while the switch is off so the connection can be checked
    before committing to the automatic sweep.
    """

    store = _state().playlist_sync_store
    if store is None:
        raise ApiError(
            503, 'server.starting', 'The Spotify sync store is not ready yet'
        )
    credentials = sync_credentials()
    if not credentials.get('client_id'):
        raise ApiError(
            400,
            'spotify.not_connected',
            'Connect Spotify before syncing',
        )
    summary = await asyncio.to_thread(
        spotify_sync.run_sync,
        sync_playlists(),
        settings=_state().settings,
        store=store,
        apply=apply_sync_diff,
        credentials=credentials,
        force=True,
    )
    _persist_tokens(summary)
    summary.pop('tokens', None)
    return summary
