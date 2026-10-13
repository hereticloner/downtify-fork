"""API endpoints for playlist Collections (TDD, offline).

Mirrors the ``client`` fixture pattern from ``tests/test_audio_replace.py``.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import main
from downtify import api
from downtify import collections_api as capi


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
    assert listed.json() == [{'version': 1, 'name': 'Sabah', 'playlists': []}]

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


# ── Smart collections over HTTP ─────────────────────────────────────


def _playlist(name, files, added=0):
    return {'name': name, 'files': files, 'added': added}


def _track(file, **fields):
    return {'file': file, **fields}


def _library(monkeypatch):
    playlists = [
        _playlist('Rocky', ['rock/one.mp3']),
        _playlist('Blue', ['jazz/two.flac']),
    ]
    tracks = {
        'rock/one.mp3': _track(
            'rock/one.mp3',
            genre='Rock',
            artist='AC/DC',
            album='Back in Black',
            codec='mp3',
        ),
        'jazz/two.flac': _track(
            'jazz/two.flac',
            genre='Jazz',
            artist='Miles Davis',
            album='Kind of Blue',
            codec='flac',
        ),
    }
    plays = {'rock/one.mp3': 4, 'jazz/two.flac': 0}
    monkeypatch.setattr(
        capi, '_library_view', lambda: (playlists, tracks, plays)
    )
    return playlists


def test_collection_detail_static_still_works(client):
    client.post('/api/collections', json={'name': 'Plain'})
    resp = client.get('/api/collections/Plain')
    assert resp.status_code == 200
    body = resp.json()
    assert body['name'] == 'Plain'
    assert body['playlists'] == []
    assert body['rules'] == []


def test_collection_detail_missing_returns_404(client):
    assert client.get('/api/collections/Yok').status_code == 404


def test_save_rules_then_detail_computes_union(client, monkeypatch):
    _library(monkeypatch)
    client.downloads.mkdir(parents=True, exist_ok=True)
    (client.downloads / 'Rocky.m3u').write_text('#EXTM3U\n')
    client.post('/api/collections', json={'name': 'Smart'})
    client.post('/api/collections/Smart/items', json={'add': ['Rocky']})
    resp = client.post(
        '/api/collections/Smart/rules',
        json={'rules': [{'type': 'genre', 'value': 'Jazz'}]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()['rules'] == [{'type': 'genre', 'value': 'Jazz'}]

    body = client.get('/api/collections/Smart').json()
    assert body['playlists'] == ['Rocky', 'Blue']
    assert body['computed'] == ['Blue']


def test_save_rules_rejects_bad_payload(client):
    client.post('/api/collections', json={'name': 'Smart'})
    resp = client.post(
        '/api/collections/Smart/rules',
        json={'rules': [{'type': 'bpm', 'value': 120}]},
    )
    assert resp.status_code == 400


def test_save_rules_unknown_collection_returns_404(client):
    resp = client.post(
        '/api/collections/Yok/rules',
        json={'rules': [{'type': 'genre', 'value': 'Rock'}]},
    )
    assert resp.status_code == 404


def test_list_computes_only_when_a_collection_has_rules(client, monkeypatch):
    _library(monkeypatch)
    client.post('/api/collections', json={'name': 'Plain'})
    listed = client.get('/api/collections').json()
    assert listed == [{'version': 1, 'name': 'Plain', 'playlists': []}]

    client.post(
        '/api/collections/Plain/rules',
        json={'rules': [{'type': 'genre', 'value': 'Rock'}]},
    )
    listed = client.get('/api/collections').json()
    assert listed[0]['playlists'] == ['Rocky']
    assert listed[0]['rules'] == [{'type': 'genre', 'value': 'Rock'}]


def test_smart_collection_reads_a_real_empty_library(client):
    # No monkeypatched view: this exercises the real library helpers
    # against the fixture's (empty) downloads folder.
    client.post('/api/collections', json={'name': 'Smart'})
    resp = client.post(
        '/api/collections/Smart/rules',
        json={'rules': [{'type': 'genre', 'value': 'Rock'}]},
    )
    assert resp.status_code == 200, resp.text
    body = client.get('/api/collections/Smart').json()
    assert body['playlists'] == []
    assert body['rules'] == [{'type': 'genre', 'value': 'Rock'}]
