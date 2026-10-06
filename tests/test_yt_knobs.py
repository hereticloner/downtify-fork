"""YouTube reliability knobs in Settings (NG idea, TDD, offline)."""

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


def test_settings_update_applies_yt_knobs_to_downloader(client):
    resp = client.post(
        '/api/settings/update',
        json={
            'yt_player_clients': ['tv', 'web'],
            'yt_po_tokens': ['mweb.gvs+abc'],
        },
    )
    assert resp.status_code == 200, resp.text
    dl = api.state.downloader
    assert dl is not None
    assert dl.yt_player_clients == ['tv', 'web']
    assert dl.yt_po_tokens == ['mweb.gvs+abc']
    assert api.state.settings['yt_player_clients'] == ['tv', 'web']


def test_settings_empty_yt_knobs_fall_back_to_none(client):
    resp = client.post(
        '/api/settings/update',
        json={'yt_player_clients': ['tv']},
    )
    assert resp.status_code == 200
    resp = client.post(
        '/api/settings/update',
        json={'yt_player_clients': []},
    )
    assert resp.status_code == 200
    assert api.state.downloader.yt_player_clients is None
