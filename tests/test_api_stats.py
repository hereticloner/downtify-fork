"""Stats endpoint (TDD, offline): library + download + playback numbers.

Aggregates from existing stores only: track index (library size),
playlist batch store (batches), activity log (downloads & playback),
likes, and the plays the Spotify history import mirrored. No new tables.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from starlette.testclient import TestClient

import main
from downtify import api, spotify_history


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
        'spotify',
    }
    assert isinstance(data['library']['likes'], int)
    assert isinstance(data['library']['tracks'], int)
    assert isinstance(data['downloads']['total'], int)
    assert isinstance(data['downloads']['last_30_days'], int)
    assert isinstance(data['playback']['total'], int)
    assert isinstance(data['playback']['top_tracks'], list)
    assert isinstance(data['spotify']['recent'], list)
    assert isinstance(data['spotify']['play_count'], int)


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


def test_stats_reports_mirrored_spotify_plays(client, monkeypatch):
    """The plays the history import stored ride along in `spotify`."""

    seen: dict[str, object] = {}

    def fake_recent(db_path, limit=50):
        seen['db_path'] = db_path
        seen['limit'] = limit
        return [
            {
                'played_at': '2026-10-12T21:15:00+00:00',
                'artist_name': 'The Night Owls',
                'track_name': 'Do I Still Recall',
                'album_name': 'Night Owls',
                'spotify_track_id': 'abc',
                'duration_ms': 201000,
                'synced_at': '2026-10-13T00:00:00+00:00',
            },
            {
                'played_at': '2026-10-12T20:58:00+00:00',
                'artist_name': 'Blue Static',
                'track_name': 'Long Way Down',
            },
        ]

    monkeypatch.setattr(
        spotify_history, 'get_recent_from_spotify', fake_recent
    )
    monkeypatch.setattr(spotify_history, 'count_plays', lambda db_path: 12)

    data = client.get('/api/stats').json()

    assert Path(seen['db_path']).name == 'downtify_activity.db'
    assert data['spotify']['play_count'] == 12
    assert data['spotify']['recent'][0] == {
        'played_at': '2026-10-12T21:15:00+00:00',
        'artist_name': 'The Night Owls',
        'track_name': 'Do I Still Recall',
        'album_name': 'Night Owls',
    }
    assert data['spotify']['recent'][1]['track_name'] == 'Long Way Down'


def test_stats_caps_the_spotify_panel_at_ten(client, monkeypatch):
    """The store keeps a page of fifty; the response lists ten."""

    rows = [
        {
            'played_at': f'2026-10-12T21:{minute:02d}:00+00:00',
            'artist_name': 'Blue Static',
            'track_name': f'Song {minute}',
        }
        for minute in range(12)
    ]
    monkeypatch.setattr(
        spotify_history, 'get_recent_from_spotify', lambda db, limit=50: rows
    )
    data = client.get('/api/stats').json()
    recent = data['spotify']['recent']
    assert len(recent) == 10
    assert recent[0] == {**rows[0], 'album_name': ''}
    assert recent[-1]['track_name'] == 'Song 9'
    # Never fewer than the list itself shows.
    assert data['spotify']['play_count'] == 10


def test_stats_spotify_survives_a_broken_history_store(client, monkeypatch):
    """A history store that cannot be read is an empty panel, not a 500."""

    def boom(*args, **kwargs):
        raise sqlite3.OperationalError('no such table')

    monkeypatch.setattr(spotify_history, 'get_recent_from_spotify', boom)
    resp = client.get('/api/stats')
    assert resp.status_code == 200, resp.text
    assert resp.json()['spotify'] == {'recent': [], 'play_count': 0}
