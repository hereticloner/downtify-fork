"""Cross-device playback resume for the signed-in user."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from downtify import api

router = APIRouter()


def _me(request: Request) -> Any:
    principal = api.principal_of(request)
    if principal is None or not principal.user_id:
        raise HTTPException(status_code=401, detail='Sign in required')
    return principal


def _store() -> Any:
    store = api.state.playback
    if store is None:
        raise HTTPException(status_code=503, detail='Starting up')
    return store


@router.get('/api/playback/resume')
def resume(request: Request) -> dict[str, Any]:
    me = _me(request)
    item = _store().latest(me.user_id)
    if item is None:
        return {
            'track': None,
            'position': 0.0,
            'duration': 0.0,
            'device_id': '',
            'player': '',
            'updated_at': '',
        }
    return item


@router.get('/api/playback/positions')
def positions(
    request: Request, limit: int = Query(20, ge=1, le=100)
) -> dict[str, Any]:
    me = _me(request)
    return {'items': _store().positions(me.user_id, limit=limit)}
