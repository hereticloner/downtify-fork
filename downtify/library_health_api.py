"""Admin-only, read-only library diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Response

from . import api as api_mod
from .library_catalog import LibraryContext, library_context_from_state
from .library_health import redact_health_report, scan_library_health

router = APIRouter()


def _context() -> LibraryContext:
    from main import DOWNLOAD_DIR  # noqa: PLC0415

    return library_context_from_state(
        Path(DOWNLOAD_DIR),
        api_mod.state.settings,
        api_mod.state.track_index,
        metadata_cache=api_mod.state.metadata_cache,
        playlist_catalog=api_mod.state.playlist_catalog,
    )


def _report() -> dict[str, Any]:
    return scan_library_health(
        _context(),
        track_index=api_mod.state.track_index,
        playlist_catalog=api_mod.state.playlist_catalog,
        monitor_db=api_mod.state.monitor_db,
        navidrome_index=api_mod.state.navidrome_index,
    )


@router.get('/api/library/health')
def library_health_report() -> dict[str, Any]:
    return _report()


@router.get('/api/library/health/export')
def library_health_export() -> Response:
    report = _report()
    return Response(
        content=json.dumps(
            redact_health_report(report), ensure_ascii=False, indent=2
        ),
        media_type='application/json',
        headers={
            'Content-Disposition': 'attachment; filename="downtify-library-health.json"'
        },
    )
