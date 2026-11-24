from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import main
from downtify import api
from downtify.download_failures import DownloadFailureStore

PASSWORD = 'failure-password'


@pytest.fixture
def client(tmp_path, monkeypatch):
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html>Downtify</html>')
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', tmp_path / 'downloads')
    monkeypatch.setattr(main, 'DATABASE_DIR', tmp_path / 'data')
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))
    monkeypatch.setattr(api.state, 'download_jobs', {})
    data = tmp_path / 'data'
    data.mkdir()
    monkeypatch.setattr(
        api.state,
        'download_failures',
        DownloadFailureStore(data / 'library.db'),
    )
    monkeypatch.setattr(api.state, 'activity', None)
    monkeypatch.setattr(api.state, 'playback', None)
    app = TestClient(main.build_app(), base_url='http://testserver')
    app.post(
        '/api/auth/login', json={'username': 'admin', 'password': 'downtify'}
    )
    return app


def _failure(client):
    return api.state.download_failures.record(
        song_id='track-1',
        song={'song_id': 'track-1', 'name': 'One', 'artist': 'A'},
        message='No audio match',
        code='no_audio_match',
    )


def test_failure_center_requires_authentication(client):
    client.cookies.clear()
    assert client.get('/api/download-failures').status_code == 401


def test_signed_in_user_can_read_failures(client):
    user = api.state.auth.users.create('reader', PASSWORD)
    _device, token = api.state.auth.create_device('phone', user_id=user['id'])
    _failure(client)

    response = client.get(
        '/api/download-failures',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data['count'] == 1
    assert data['items'][0]['song_id'] == 'track-1'
    assert data['items'][0]['attempts'] == 1


def test_retry_queues_without_resolving_the_failure(client, monkeypatch):
    _failure(client)

    async def fake_run_download(*args, **kwargs):
        return None

    monkeypatch.setattr(api, '_run_download', fake_run_download)
    response = client.post(
        '/api/download-failures/retry', json={'song_id': 'track-1'}
    )

    assert response.status_code == 200, response.text
    assert response.json() == {'queued': True, 'song_id': 'track-1'}
    assert 'track-1' in api.state.download_jobs
    assert api.state.download_failures.list()[0]['resolved_at'] is None


def test_clear_removes_only_resolved_failures(client):
    store = api.state.download_failures
    _failure(client)
    store.record(song_id='track-2', song={'name': 'Two'}, message='failed')
    store.resolve('track-2')

    response = client.delete('/api/download-failures')

    assert response.status_code == 200, response.text
    assert response.json() == {'cleared': 1}
    assert [row['song_id'] for row in store.list()] == ['track-1']
