from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import main
from downtify import api

PASSWORD = 'resume-password'


@pytest.fixture
def client(tmp_path, monkeypatch):
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html>Downtify</html>')
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', tmp_path / 'downloads')
    monkeypatch.setattr(main, 'DATABASE_DIR', tmp_path / 'data')
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))
    return TestClient(main.build_app(), base_url='http://testserver')


def _paired(client, username: str) -> tuple[dict[str, str], int]:
    user = api.state.auth.users.create(username, PASSWORD)
    device, token = api.state.auth.create_device(
        f'{username} phone', user_id=user['id']
    )
    return {'Authorization': f'Bearer {token}'}, user['id']


def test_resume_returns_the_users_latest_device_position(client):
    headers, user_id = _paired(client, 'resume')
    _device, token = api.state.auth.create_device('tablet', user_id=user_id)
    tablet = {'Authorization': f'Bearer {token}'}
    track = {'file': 'A - One.mp3', 'title': 'One', 'duration': 100}

    first = client.post(
        '/api/activity/playback',
        json={
            'player': 'app',
            'state': 'paused',
            'track': track,
            'position': 10,
        },
        headers=headers,
    )
    assert first.status_code == 200, first.text
    second = client.post(
        '/api/activity/playback',
        json={
            'player': 'app',
            'state': 'paused',
            'track': track,
            'position': 42,
        },
        headers=tablet,
    )
    assert second.status_code == 200, second.text

    resume = client.get('/api/playback/resume', headers=headers)
    assert resume.status_code == 200, resume.text
    data = resume.json()
    assert data['track']['file'] == 'A - One.mp3'
    assert data['position'] == 42
    assert data['device_id']
    positions = client.get('/api/playback/positions', headers=headers)
    assert positions.status_code == 200
    assert len(positions.json()['items']) == 2


def test_resume_is_user_scoped(client):
    _paired(client, 'first')
    second, _user_id = _paired(client, 'second')

    response = client.get('/api/playback/resume', headers=second)
    assert response.status_code == 200
    assert response.json()['track'] is None
    assert response.json()['position'] == 0


def test_deleting_a_user_removes_playback_state(client):
    login = client.post(
        '/api/auth/login', json={'username': 'admin', 'password': 'downtify'}
    )
    assert login.status_code == 200, login.text
    headers, user_id = _paired(client, 'victim')
    client.post(
        '/api/activity/playback',
        json={
            'player': 'app',
            'state': 'paused',
            'track': {'file': 'A - One.mp3', 'duration': 100},
            'position': 12,
        },
        headers=headers,
    )
    assert api.state.playback.latest(user_id) is not None

    response = client.delete(f'/api/users/{user_id}')
    assert response.status_code == 200, response.text
    assert api.state.playback.latest(user_id) is None


def test_resume_requires_authentication(client):
    assert client.get('/api/playback/resume').status_code == 401
    assert client.get('/api/playback/positions').status_code == 401
