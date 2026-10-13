"""FastAPI router for playlist Collections.

Kept as its own module so upstream merges into ``api.py`` never touch it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from . import collections as coll
from . import stats as stats_mod
from .library_paths_cache import invalidate_library_paths_cache

router = APIRouter()


def _download_dir() -> Any:
    from main import DOWNLOAD_DIR  # noqa: PLC0415

    return DOWNLOAD_DIR


def _raise(exc: BaseException) -> None:
    status = getattr(exc, 'status_code', 400)
    raise HTTPException(status_code=status, detail=str(exc)) from exc


# ── The library snapshot smart rules are evaluated against ──────────
#
# Each helper is one piece of the snapshot the API layer already keeps
# warm (the playlist listing and the library metadata cache). They are
# plain functions so tests can swap them for a synthetic library.


def _library_context() -> Any:
    from downtify import api as api_mod  # noqa: PLC0415
    from main import DOWNLOAD_DIR  # noqa: PLC0415

    from .library_catalog import (  # noqa: PLC0415
        library_context_from_state,
    )

    return library_context_from_state(
        Path(DOWNLOAD_DIR),
        api_mod.state.settings,
        api_mod.state.track_index,
        metadata_cache=api_mod.state.metadata_cache,
        playlist_catalog=api_mod.state.playlist_catalog,
    )


def _list_playlists(ctx: Any) -> list[dict[str, Any]]:
    from .playlist_listing import list_library_playlists  # noqa: PLC0415

    return list_library_playlists(
        ctx.download_dir, ctx.slskd_dir, ctx.extra_dirs, stale_ok=True
    )


def _tracks_by_file(ctx: Any) -> dict[str, dict[str, Any]]:
    from .library_catalog import listing_for_request  # noqa: PLC0415

    return {
        str(entry.get('file') or ''): entry
        for entry in listing_for_request(ctx)
    }


def _play_counts() -> dict[str, int]:
    from downtify import api as api_mod  # noqa: PLC0415

    log = api_mod.state.activity
    if log is None:
        return {}
    counts: dict[str, int] = {}
    before = 0
    while True:
        page = log.entries(kinds=['playback'], limit=200, before=before)
        entries = page.get('entries') or []
        for entry in entries:
            detail = entry.get('detail') or {}
            track = detail.get('track') or {}
            name = str(track.get('file') or '').strip().replace('\\', '/')
            if name:
                counts[name] = counts.get(name, 0) + 1
        nxt = int(page.get('next') or 0)
        if not nxt or not entries:
            break
        before = nxt
    return counts


def _library_view() -> tuple[
    list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, int]
]:
    """The playlists, their tracks and per-file play counts, all at once."""

    ctx = _library_context()
    return _list_playlists(ctx), _tracks_by_file(ctx), _play_counts()


@router.get('/api/collections')
async def list_collections_endpoint() -> list[dict[str, Any]]:
    collections = coll.list_collections(_download_dir())
    # Only walk the library when a smart collection actually needs it; a
    # rule-less listing keeps its exact old shape.
    if not any(col.get('rules') for col in collections):
        return collections
    playlists, tracks, play_counts = _library_view()
    return [
        coll.resolve_collection(
            col,
            playlists=playlists,
            tracks=tracks,
            play_counts=play_counts,
        )
        for col in collections
    ]


@router.get('/api/collections/{name}')
async def get_collection_endpoint(name: str) -> dict[str, Any]:
    try:
        data = coll.get_collection(_download_dir(), name)
    except coll.CollectionError as exc:
        _raise(exc)
    if data.get('rules'):
        playlists, tracks, play_counts = _library_view()
        data = coll.resolve_collection(
            data,
            playlists=playlists,
            tracks=tracks,
            play_counts=play_counts,
        )
    data.setdefault('rules', [])
    return data


@router.post('/api/collections/{name}/rules')
async def set_collection_rules_endpoint(
    name: str, request: Request
) -> dict[str, Any]:
    payload = await request.json()
    try:
        return coll.set_rules(_download_dir(), name, payload.get('rules'))
    except (coll.CollectionError, coll.RuleError) as exc:
        _raise(exc)


@router.post('/api/collections')
async def create_collection_endpoint(request: Request) -> dict[str, Any]:
    payload = await request.json()
    try:
        return coll.create_collection(
            _download_dir(), str(payload.get('name') or '')
        )
    except coll.CollectionError as exc:
        _raise(exc)


@router.post('/api/collections/{name}')
async def rename_collection_endpoint(
    name: str, request: Request
) -> dict[str, Any]:
    payload = await request.json()
    try:
        return coll.rename_collection(
            _download_dir(), name, str(payload.get('name') or '')
        )
    except coll.CollectionError as exc:
        _raise(exc)


@router.post('/api/collections/{name}/items')
async def edit_collection_items_endpoint(
    name: str, request: Request
) -> dict[str, Any]:
    payload = await request.json()
    add = payload.get('add') if isinstance(payload.get('add'), list) else []
    remove = (
        payload.get('remove')
        if isinstance(payload.get('remove'), list)
        else []
    )
    try:
        data = coll.add_to_collection(
            _download_dir(), name, [str(i) for i in add]
        )
        data = coll.remove_from_collection(
            _download_dir(), name, [str(i) for i in remove]
        )
        invalidate_library_paths_cache()
        return data
    except coll.CollectionError as exc:
        _raise(exc)


@router.get('/api/stats')
async def stats_endpoint() -> dict[str, Any]:
    from downtify import api as api_mod  # noqa: PLC0415

    st = api_mod.state
    track_count = 0
    if st.track_index is not None:
        track_count = len(st.track_index.list_filenames())
    playlist_count = 0
    try:
        from main import DOWNLOAD_DIR  # noqa: PLC0415

        playlist_count = len([
            p
            for p in api_mod.list_library_playlists(
                DOWNLOAD_DIR, None, None, stale_ok=True
            )
        ])
    except Exception:
        playlist_count = 0
    likes = 0
    try:
        likes = st.likes.count() if st.likes is not None else 0
    except Exception:
        likes = 0
    activity = st.activity
    if activity is None:
        return {
            'library': {'tracks': 0, 'playlists': 0, 'likes': 0},
            'downloads': {'total': 0, 'last_30_days': 0, 'per_day': []},
            'playback': {'total': 0, 'top_tracks': []},
        }
    return stats_mod.build_stats(
        activity=activity,
        track_count=track_count,
        likes=likes,
        playlist_count=playlist_count,
    )


@router.delete('/api/collections/{name}')
async def delete_collection_endpoint(name: str) -> dict[str, Any]:
    try:
        return coll.delete_collection(_download_dir(), name)
    except coll.CollectionError as exc:
        _raise(exc)
