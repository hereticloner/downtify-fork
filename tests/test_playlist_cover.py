"""Custom covers for manual playlists (upstream PR #525 port):
``PUT /api/library/playlists/cover`` and
``DELETE /api/library/playlists/cover``. Offline — no files on disk,
``save``/``remove`` are stubbed."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from downtify import api
from downtify.auth import ADMIN, classify
from downtify.library_catalog import LibraryContext

_ENTRY = {
    'name': 'Mix',
    'files': [],
    'count': 0,
    'added': 1,
    'cover': '',
    'liked': False,
    'manual': True,
    'explicit_cover': False,
}


def _request(data: bytes = b'jpeg') -> Request:
    sent = False
    scope = {
        'type': 'http',
        'headers': [(b'content-type', b'image/jpeg')],
        'query_string': b'',
        'state': {},
    }

    async def receive() -> dict[str, Any]:
        nonlocal sent
        if sent:
            return {'type': 'http.request', 'body': b'', 'more_body': False}
        sent = True
        return {'type': 'http.request', 'body': data, 'more_body': False}

    return Request(scope, receive)


@pytest.fixture
def world(tmp_path, monkeypatch):
    ctx = LibraryContext(download_dir=tmp_path)
    monkeypatch.setattr(api, 'library_context', lambda: ctx)
    monkeypatch.setattr(
        api, 'list_library_playlists', lambda *a, **k: [_ENTRY]
    )

    async def _noop() -> None:
        return None

    monkeypatch.setattr(api, 'announce_playlists_changed', _noop)
    saved: list[tuple[Any, ...]] = []

    def _save(context, name, data, content_type):
        saved.append((context, name, data, content_type))
        return tmp_path / 'Mix.jpg'

    monkeypatch.setattr(api, 'save_manual_playlist_cover', _save)
    return saved


def test_upload_reports_pixels_for_a_manual_playlist(world):
    result = asyncio.run(
        api.upload_library_playlist_cover_endpoint(
            _request(b'raw'), name='Mix'
        )
    )
    assert result == {'ok': True}
    (recorded_ctx, name, data, content_type) = world[0]
    assert (name, data, content_type) == ('Mix', b'raw', 'image/jpeg')


def test_upload_refuses_missing_and_non_manual_playlists(world):
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            api.upload_library_playlist_cover_endpoint(_request(), name='Nope')
        )
    assert error.value.status_code == 404


def test_upload_refuses_a_non_manual_entry(world, monkeypatch):
    monkeypatch.setattr(
        api,
        'list_library_playlists',
        lambda *a, **k: [{**_ENTRY, 'manual': False}],
    )
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            api.upload_library_playlist_cover_endpoint(_request(), name='Mix')
        )
    assert error.value.status_code == 403


def test_invalid_and_unconvertible_images_are_400_and_503(world, monkeypatch):
    monkeypatch.setattr(
        api,
        'save_manual_playlist_cover',
        lambda *a, **k: (_ for _ in ()).throw(
            ValueError('Upload a valid JPEG, PNG or WebP image')
        ),
    )
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            api.upload_library_playlist_cover_endpoint(
                _request(b'junk'), name='Mix'
            )
        )
    assert error.value.status_code == 400

    monkeypatch.setattr(
        api,
        'save_manual_playlist_cover',
        lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError('Image conversion is unavailable')
        ),
    )
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            api.upload_library_playlist_cover_endpoint(
                _request(b'junk'), name='Mix'
            )
        )
    assert error.value.status_code == 503


def test_upload_enforces_the_10_mib_limit(world):
    big = b'x' * (10 * 1024 * 1024 + 1)
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            api.upload_library_playlist_cover_endpoint(
                _request(big), name='Mix'
            )
        )
    assert error.value.status_code == 413


def test_remove_cover(world, monkeypatch):
    removed: list[str] = []

    def _remove(context, name):
        removed.append(name)

    monkeypatch.setattr(api, 'remove_manual_playlist_cover', _remove)
    result = asyncio.run(
        api.remove_library_playlist_cover_endpoint(_request(), name='Mix')
    )
    assert result == {'ok': True}
    assert removed == ['Mix']


def test_remove_refuses_unknown_playlist(world):
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            api.remove_library_playlist_cover_endpoint(_request(), name='Nope')
        )
    assert error.value.status_code == 404


def test_the_routes_are_for_admins():
    assert classify('PUT', '/api/library/playlists/cover') == ADMIN
    assert classify('DELETE', '/api/library/playlists/cover') == ADMIN
