from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from downtify import api

router = APIRouter()
_SCHEDULES = {'off': 0, 'daily': 1, 'three_days': 3, 'weekly': 7}


def _store():
    store = api.state.backup_store
    if store is None:
        raise HTTPException(status_code=503, detail='Starting up')
    return store


def _schedule_path() -> Path:
    return _store().data_dir / 'backup-schedule.json'


def _read_schedule() -> str:
    try:
        value = json.loads(_schedule_path().read_text())['schedule']
    except (OSError, ValueError, KeyError, TypeError):
        return 'off'
    return value if value in _SCHEDULES else 'off'


@router.get('/api/backups/schedule')
def get_schedule() -> dict[str, Any]:
    return {'schedule': _read_schedule()}


@router.post('/api/backups/schedule')
async def set_schedule(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    value = str(body.get('schedule') or 'off')
    if value not in _SCHEDULES:
        raise HTTPException(status_code=400, detail='Unknown backup schedule')
    path = _schedule_path()
    partial = path.with_name(f'.{path.name}.partial')
    payload = json.dumps({'schedule': value}).encode()
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)
    return {'schedule': value}


async def backup_schedule_loop() -> None:
    """Create a backup when the configured number of days has elapsed."""

    while True:
        try:
            store = _store()
            schedule = _read_schedule()
            days = _SCHEDULES[schedule]
            if days:
                latest = store.list()
                age_days = (
                    (
                        datetime.now(timezone.utc).timestamp()
                        - latest[0].stat().st_mtime
                    )
                    / 86400
                    if latest
                    else days
                )
                if age_days >= days:
                    path = await asyncio.to_thread(store.write)
                    await api.notify_event(
                        'backup.completed',
                        {'name': path.name, 'scheduled': True},
                    )
        except Exception:
            api.logger.exception('Scheduled backup failed')
        await asyncio.sleep(3600)
