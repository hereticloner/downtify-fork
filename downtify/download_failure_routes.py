"""Persistent download failure center for the Queue page."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from downtify import api

router = APIRouter()


def _store() -> Any:
    store = api.state.download_failures
    if store is None:
        raise HTTPException(status_code=503, detail='Starting up')
    return store


@router.get('/api/download-failures')
def list_failures() -> dict[str, Any]:
    items = _store().list()
    return {'items': items, 'count': len(items)}


@router.delete('/api/download-failures')
def clear_failures() -> dict[str, Any]:
    return {'cleared': _store().clear()}


@router.post('/api/download-failures/retry')
async def retry_failure(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    song_id = str(body.get('song_id') or '').strip()
    if not song_id:
        raise HTTPException(status_code=400, detail='song_id is required')
    found = next(
        (row for row in _store().list() if row['song_id'] == song_id), None
    )
    if found is None:
        raise HTTPException(status_code=404, detail='Failure not found')
    song = dict(found['song'])
    song['song_id'] = song_id
    existing = api.state.download_jobs.get(song_id)
    if existing and existing.get('status') in {
        'queued',
        'downloading',
        'active',
    }:
        raise HTTPException(status_code=409, detail='Already queued')
    api._register_job(song, status='queued')
    pending = api._pending_download(song, song_id)
    await api._remember_pending([pending])
    api.spawn_task(
        api._run_download(song, song_id, pending_saved=True),
        name=f'failure-retry-{song_id}',
    )
    return {'queued': True, 'song_id': song_id}
