"""Stats endpoint (TDD, offline): library + download + playback numbers.

Aggregates from existing stores only: track index (library size),
playlist batch store (batches), activity log (downloads & playback),
likes. No new tables.
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
    downloads.mkdir()
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
        'playlist_batch_store',
    ):
        monkeypatch.setattr(api.state, name, getattr(api.state, name))
    monkeypatch.setattr(api.state, 'download_jobs', {})
    app = TestClient(main.build_app(), base_url='http://testserver')
    app.post(
        '/api/auth/login', json={'username': 'admin', 'password': 'downtify'}
    )
    app.downloads = downloads
    return app


def test_stats_endpoint_shape_with_empty_stores(client):
    resp = client.get('/api/stats')
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert set(data) >= {
        'library',
        'downloads',
        'playback',
    }
    assert isinstance(data['library']['likes'], int)
    assert isinstance(data['library']['tracks'], int)
    assert isinstance(data['downloads']['total'], int)
    assert isinstance(data['downloads']['last_30_days'], int)
    assert isinstance(data['playback']['total'], int)
    assert isinstance(data['playback']['top_tracks'], list)


def test_stats_counts_activity_kinds(client):
    """Downloads and playback are read from the activity log."""

    log = api.state.activity
    assert log is not None
    log.record('download', summary='Song A')
    log.record('download', summary='Song B')
    log.record('playback', summary='Song A')
    resp = client.get('/api/stats')
    data = resp.json()
    assert data['downloads']['total'] >= 2
    assert data['playback']['total'] >= 1
    assert data['playback']['top_tracks'][0]['summary'] == 'Song A'
