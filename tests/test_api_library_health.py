from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

import main
from downtify import api, auth_routes, library_health
from downtify import library_health_api as health_api
from downtify.auth import ADMIN, AuthMiddleware, AuthStore, classify
from downtify.track_index import TrackIndex

TRACK_ID = '4uLU6hMCjMI75M1A2tKUQC'
PASSWORD = 'correct horse battery'


@pytest.fixture(autouse=True)
def readable_metadata(monkeypatch):
    monkeypatch.setattr(
        library_health,
        'read_audio_metadata',
        lambda path: {'title': 'Title', 'artist': 'Artist'},
    )


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    data = tmp_path / 'data'
    data.mkdir()
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', downloads)
    monkeypatch.setattr(api.state, 'settings', {})
    for name in (
        'metadata_cache',
        'track_index',
        'playlist_catalog',
        'monitor_db',
        'navidrome_index',
    ):
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


def test_health_report_returns_scanner_shape(
    client: TestClient, tmp_path: Path, monkeypatch
) -> None:
    index = TrackIndex(tmp_path / 'library.db')
    index.register(TRACK_ID, 'Artist/Missing.mp3')
    monkeypatch.setattr(api.state, 'track_index', index)
    _login(client)

    response = client.get('/api/library/health')

    assert response.status_code == 200, response.text
    report = response.json()
    assert set(report) == {
        'version',
        'scanned_at',
        'summary',
        'sources',
        'findings',
        'warnings',
    }
    assert report['summary']['findings'] == 1
    assert report['findings'][0]['category'] == 'orphan_record'


def test_health_export_is_redacted_json(
    client: TestClient, tmp_path: Path, monkeypatch
) -> None:
    secret_path = 'Private/Secret Token.mp3'
    index = TrackIndex(tmp_path / 'library.db')
    index.register(TRACK_ID, secret_path)
    monkeypatch.setattr(api.state, 'track_index', index)
    _login(client)

    response = client.get('/api/library/health/export')

    assert response.status_code == 200, response.text
    assert response.headers['content-type'].startswith('application/json')
    assert 'attachment' in response.headers['content-disposition']
    assert (
        'downtify-library-health.json'
        in response.headers['content-disposition']
    )
    exported = json.loads(response.content)
    assert exported['summary']['findings'] == 1
    assert exported['findings'][0]['category'] == 'orphan_record'
    assert secret_path not in response.text
    assert TRACK_ID not in response.text
    assert 'file' not in exported['findings'][0]
    assert 'record_id' not in exported['findings'][0]


def test_health_routes_are_admin_only(client: TestClient) -> None:
    assert classify('GET', '/api/library/health') == ADMIN
    assert classify('GET', '/api/library/health/export') == ADMIN
    assert client.get('/api/library/health').status_code == 401
    assert client.get('/api/library/health/export').status_code == 401

    api.state.auth.users.create('maria', PASSWORD)
    _login(client, 'maria', PASSWORD)
    assert client.get('/api/library/health').status_code == 403
    assert client.get('/api/library/health/export').status_code == 403


def test_health_routes_do_not_write(
    client: TestClient, tmp_path: Path, monkeypatch
) -> None:
    track = main.DOWNLOAD_DIR / 'Artist/Track.mp3'
    track.parent.mkdir(parents=True)
    track.write_bytes(b'audio-bytes')
    index = TrackIndex(tmp_path / 'library.db')
    index.register(TRACK_ID, 'Artist/Track.mp3', full_path=track)
    monkeypatch.setattr(api.state, 'track_index', index)
    _login(client)
    before = (
        track.read_bytes(),
        sorted(
            path.relative_to(main.DOWNLOAD_DIR)
            for path in main.DOWNLOAD_DIR.rglob('*')
            if path.is_file()
        ),
        index.all_rows(),
    )

    assert client.get('/api/library/health').status_code == 200
    assert client.get('/api/library/health/export').status_code == 200

    assert track.read_bytes() == before[0]
    assert (
        sorted(
            path.relative_to(main.DOWNLOAD_DIR)
            for path in main.DOWNLOAD_DIR.rglob('*')
            if path.is_file()
        )
        == before[1]
    )
    assert index.all_rows() == before[2]


def test_main_includes_health_routes(tmp_path: Path, monkeypatch) -> None:
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html>Downtify</html>')
    monkeypatch.setattr(main, 'DATABASE_DIR', tmp_path / 'data')
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))

    app = main.build_app()

    paths = app.openapi()['paths']
    assert '/api/library/health' in paths
    assert '/api/library/health/export' in paths
