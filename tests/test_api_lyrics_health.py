from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

import main
from downtify import api, auth_routes
from downtify import lyrics_health_api as health_api
from downtify.auth import ADMIN, AuthMiddleware, AuthStore, classify

PASSWORD = 'correct horse battery'


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    data = tmp_path / 'data'
    data.mkdir()
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', downloads)
    monkeypatch.setattr(
        api.state,
        'settings',
        {'download_lyrics': True, 'lyrics_providers': ['lrclib']},
    )
    for name in ('track_index', 'playlist_catalog', 'lyrics_cache'):
        monkeypatch.setattr(api.state, name, None)
    auth = AuthStore(data / 'auth.db', data / '.secret')
    auth.users.ensure_default_admin(existing_install=False)
    monkeypatch.setattr(api.state, 'auth', auth)
    app = FastAPI()
    app.add_middleware(
        AuthMiddleware,
        get_store=lambda: auth,
        get_tickets=lambda: None,
    )
    app.include_router(health_api.router)
    app.include_router(auth_routes.router)
    return TestClient(app, base_url='http://testserver')


def _login(client, username='admin', password='downtify') -> None:
    response = client.post(
        '/api/auth/login', json={'username': username, 'password': password}
    )
    assert response.status_code == 200


def test_lyrics_health_routes_are_admin_only(client):
    assert classify('GET', '/api/lyrics/health') == ADMIN
    assert classify('POST', '/api/lyrics/health/fill') == ADMIN
    assert client.get('/api/lyrics/health').status_code == 401
    assert (
        client.post('/api/lyrics/health/fill', json={'files': []}).status_code
        == 401
    )

    api.state.auth.users.create('maria', PASSWORD)
    _login(client, 'maria', PASSWORD)
    assert client.get('/api/lyrics/health').status_code == 403
    assert (
        client.post('/api/lyrics/health/fill', json={'files': []}).status_code
        == 403
    )


def test_health_report_returns_scanner_shape_without_filling(
    client, monkeypatch
):
    report = {
        'version': 1,
        'scanned_at': '2026-11-25T00:00:00+00:00',
        'summary': {'tracks': 0, 'synced': 0, 'plain_only': 0, 'missing': 0},
        'findings': [],
    }
    monkeypatch.setattr(
        health_api, 'scan_lyrics_health', lambda *_a, **_k: report
    )

    def never(*_a, **_k):
        raise AssertionError('GET must not fill')

    monkeypatch.setattr(health_api, 'fill_lyrics', never)
    _login(client)

    response = client.get('/api/lyrics/health')

    assert response.status_code == 200
    assert response.json() == {**report, 'synced_only': False}


def test_fill_rejects_more_than_100_files(client, monkeypatch):
    def never(*_a, **_k):
        raise AssertionError('limit must be checked before filling')

    monkeypatch.setattr(health_api, 'fill_lyrics', never)
    _login(client)

    response = client.post(
        '/api/lyrics/health/fill',
        json={'files': [f'{number}.mp3' for number in range(101)]},
    )

    assert response.status_code == 400


def test_fill_rejects_disabled_lyrics(client, monkeypatch):
    monkeypatch.setitem(api.state.settings, 'download_lyrics', False)
    _login(client)

    response = client.post(
        '/api/lyrics/health/fill', json={'files': ['Song.mp3']}
    )

    assert response.status_code == 400
    assert response.json()['detail'] == 'Lyrics downloads are disabled'


def test_fill_returns_the_core_result(client, monkeypatch):
    result = {
        'requested': 1,
        'found': 1,
        'written': 1,
        'skipped': 0,
        'failed': 0,
        'errors': [],
    }
    seen = []

    def fill(files, *_a, **_k):
        seen.append(files)
        return result

    monkeypatch.setattr(health_api, 'fill_lyrics', fill)
    _login(client)

    response = client.post(
        '/api/lyrics/health/fill', json={'files': ['Song.mp3']}
    )

    assert response.status_code == 200
    assert response.json() == result
    assert seen == [['Song.mp3']]
