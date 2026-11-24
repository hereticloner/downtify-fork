"""Admin-only metadata backup, download, upload and restore routes."""

from __future__ import annotations

import asyncio
import gzip
import json
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from downtify import api
from downtify.backup import BackupStore
from downtify.backup_schedule import _read_schedule
from downtify.backup_schedule import router as schedule_router

router = APIRouter()
router.include_router(schedule_router)
_NAME_RE = re.compile(r'^downtify-[A-Za-z0-9._-]+\.json\.gz$')
_MAX_UPLOAD_BYTES = 256 * 1024 * 1024


def _store() -> BackupStore:
    store = api.state.backup_store
    if store is None:
        raise HTTPException(status_code=503, detail='Starting up')
    return store


def _path(name: str) -> Path:
    if not _NAME_RE.fullmatch(name):
        raise HTTPException(status_code=400, detail='Invalid backup name')
    path = _store().backup_dir / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail='Backup not found')
    return path


def _item(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        'name': path.name,
        'size': stat.st_size,
        'created_at': stat.st_mtime,
    }


@router.get('/api/backups')
def list_backups() -> dict[str, Any]:
    items = [_item(path) for path in _store().list()]
    return {
        'items': items,
        'count': len(items),
        'schedule': _read_schedule(),
    }


@router.post('/api/backups')
async def create_backup() -> dict[str, Any]:
    path = await asyncio.to_thread(_store().write)
    await api.notify_event('backup.completed', {'name': path.name})
    return _item(path)


@router.get('/api/backups/{name}')
def download_backup(name: str) -> FileResponse:
    return FileResponse(
        _path(name),
        media_type='application/gzip',
        filename=name,
    )


@router.delete('/api/backups/{name}')
def delete_backup(name: str) -> dict[str, Any]:
    _path(name).unlink()
    return {'deleted': True, 'name': name}


@router.post('/api/backups/upload')
async def upload_backup(file: UploadFile = File(...)) -> dict[str, Any]:
    name = Path(file.filename or '').name
    if not _NAME_RE.fullmatch(name):
        raise HTTPException(status_code=400, detail='Invalid backup name')
    target = _store().backup_dir / name
    partial = target.with_name(f'.{target.name}.partial')
    _store().backup_dir.mkdir(parents=True, exist_ok=True)
    size = 0
    try:
        with partial.open('wb') as handle:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > _MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413, detail='Backup is too large'
                    )
                handle.write(chunk)
            handle.flush()
        with gzip.open(partial, 'rb') as handle:
            json.loads(handle.read())
        partial.chmod(0o600)
        partial.replace(target)
        target.chmod(0o600)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        partial.unlink(missing_ok=True)
    for old in _store().list()[2:]:
        old.unlink(missing_ok=True)
    return _item(target)


@router.post('/api/backups/restore')
async def restore_backup(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    name = str(body.get('name') or '')
    path = _path(name)
    if not isinstance(body.get('dry_run'), bool):
        raise HTTPException(
            status_code=400, detail='dry_run must be true or false'
        )
    if body['dry_run'] is False and body.get('confirm') is not True:
        raise HTTPException(
            status_code=400, detail='confirm is required to restore'
        )
    dry_run = body['dry_run'] is True
    requeue = body.get('requeue_missing') is True
    try:
        result = await asyncio.to_thread(
            _store().restore,
            path,
            dry_run=dry_run,
            requeue_missing=requeue,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not dry_run:
        if api.state.settings_path is not None:
            api.state.settings = api._load_settings(api.state.settings_path)
        await api.notify_event(
            'backup.completed', {'name': name, 'restored': True}
        )
    return result
