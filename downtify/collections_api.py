"""FastAPI router for playlist Collections.

Kept as its own module so upstream merges into ``api.py`` never touch it.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from . import collections as coll
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


@router.delete('/api/collections/{name}')
async def delete_collection_endpoint(name: str) -> dict[str, Any]:
    try:
        return coll.delete_collection(_download_dir(), name)
    except coll.CollectionError as exc:
        _raise(exc)
