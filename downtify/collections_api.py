"""FastAPI router for playlist Collections.

Kept as its own module so upstream merges into ``api.py`` never touch it.
"""

from __future__ import annotations

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


@router.get('/api/collections')
async def list_collections_endpoint() -> list[dict[str, Any]]:
    return coll.list_collections(_download_dir())


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

        playlist_count = len(
            [
                p
                for p in api_mod.list_library_playlists(
                    DOWNLOAD_DIR, None, None, stale_ok=True
                )
            ]
        )
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
