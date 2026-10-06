"""API endpoints for playlist Collections (TDD, offline).

Mirrors the ``client`` fixture pattern from ``tests/test_audio_replace.py``.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import main
from downtify import api


@pytest.fixture
def client(tmp_path, monkeypatch):
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html>Downtify</html>')
    downloads = tmp_path / 'downloads'
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', downloads)
    monkeypatch.setattr(main, 'DATABASE_DIR', tmp_path / 'data')
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))
    for name in (
        'auth',
        'activity',
        'identity',
        'downloader',
        'settings',
        'metadata_cache',
        'track_index',
        'download_jobs',
    ):
        monkeypatch.setattr(api.state, name, getattr(api.state, name))
    monkeypatch.setattr(api.state, 'download_jobs', {})
    app = TestClient(main.build_app(), base_url='http://testserver')
    app.post(
        '/api/auth/login', json={'username': 'admin', 'password': 'downtify'}
    )
    app.downloads = downloads
    return app


def test_collections_crud_over_http(client):
    resp = client.post('/api/collections', json={'name': 'Sabah'})
    assert resp.status_code == 200, resp.text
    listed = client.get('/api/collections')
    assert listed.status_code == 200
    assert listed.json() == [
        {'version': 1, 'name': 'Sabah', 'playlists': []}
    ]

    # Delete
    resp = client.request('DELETE', '/api/collections/Sabah')
    assert resp.status_code == 200
    assert client.get('/api/collections').json() == []


def test_collections_missing_returns_404(client):
    resp = client.request('DELETE', '/api/collections/Yok')
    assert resp.status_code == 404


def test_collections_rename_and_unknown_playlist(client):
    client.post('/api/collections', json={'name': 'Eski'})
    resp = client.post('/api/collections/Eski', json={'name': 'Yeni'})
    assert resp.status_code == 200
    names = [c['name'] for c in client.get('/api/collections').json()]
    assert names == ['Yeni']

    resp = client.post(
        '/api/collections/Yeni/items', json={'add': ['Olmayan']}
    )
    assert resp.status_code == 404
