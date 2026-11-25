"""Admin-only lyrics health scan and explicit fill endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from . import api as api_mod
from . import lyrics as lyrics_mod
from .library_catalog import LibraryContext, library_context_from_state
from .lyrics_health import fill_lyrics, scan_lyrics_health

router = APIRouter()
MAX_FILL_FILES = 100


def _context() -> LibraryContext:
    from main import DOWNLOAD_DIR  # noqa: PLC0415

    return library_context_from_state(
        Path(DOWNLOAD_DIR),
        api_mod.state.settings,
        api_mod.state.track_index,
        metadata_cache=api_mod.state.metadata_cache,
        playlist_catalog=api_mod.state.playlist_catalog,
    )


@router.get('/api/lyrics/health')
def lyrics_health_report() -> dict[str, Any]:
    report = scan_lyrics_health(_context(), api_mod.state.track_index)
    report['synced_only'] = bool(
        api_mod.state.settings.get('lyrics_synced_only', False)
    )
    return report


@router.post('/api/lyrics/health/fill')
def lyrics_health_fill(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    files = payload.get('files')
    if not isinstance(files, list) or any(
        not isinstance(name, str) for name in files
    ):
        raise HTTPException(status_code=400, detail='Files must be a list')
    if len(files) > MAX_FILL_FILES:
        raise HTTPException(
            status_code=400,
            detail=f'At most {MAX_FILL_FILES} files can be filled at once',
        )
    if not lyrics_mod.providers_from_settings(api_mod.state.settings):
        raise HTTPException(
            status_code=400, detail='Lyrics downloads are disabled'
        )
    return fill_lyrics(
        files,
        _context(),
        api_mod.state.settings,
        api_mod.state.lyrics_cache,
        api_mod.state.track_index,
    )
