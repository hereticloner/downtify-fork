from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from downtify import api, auth_routes
from downtify.auth import AuthMiddleware, AuthStore
from downtify.download_queue import (
    PendingDownload,
    PendingDownloads,
    queue_pause,
)


class _Connections:
    def __init__(self):
        self.messages = []

    async def broadcast(self, message):
        self.messages.append(message)


@pytest.fixture
def queue_client(tmp_path: Path, monkeypatch):
    data = tmp_path / 'data'
    data.mkdir()
    auth = AuthStore(data / 'downtify.db', data / '.secret')
    auth.users.ensure_default_admin(existing_install=False)
    auth.users.create('listener', 'password123', role='user')
    store = PendingDownloads(data / 'downtify_library.db')
    connections = _Connections()
    monkeypatch.setattr(api.state, 'auth', auth)
    monkeypatch.setattr(api.state, 'pending_downloads', store)
    monkeypatch.setattr(api.state, 'downloader', object())
    monkeypatch.setattr(api.state, 'connections', connections)

    async def no_run(rows):
        return None

    monkeypatch.setattr(api, '_run_restored_queue', no_run)
    api.state.download_jobs.clear()
    queue_pause.resume()
    clear_jobs = getattr(queue_pause, 'clear_paused_jobs', None)
    if clear_jobs is not None:
        clear_jobs()
    app = FastAPI()
    app.add_middleware(
        AuthMiddleware,
        get_store=lambda: auth,
        get_tickets=lambda: None,
    )
    app.include_router(api.router)
    app.include_router(auth_routes.router)
    yield TestClient(app, base_url='http://testserver'), store
    api.state.download_jobs.clear()
    queue_pause.resume()
    clear_jobs = getattr(queue_pause, 'clear_paused_jobs', None)
    if clear_jobs is not None:
        clear_jobs()


def _login(client, username='admin', password='downtify'):
    response = client.post(
        '/api/auth/login', json={'username': username, 'password': password}
    )
    assert response.status_code == 200


def _job(song_id: str, status: str = 'queued', priority: str = 'normal'):
    api._register_job(
        {'song_id': song_id, 'name': song_id},
        status=status,
        priority=priority,
    )


def _saved(store: PendingDownloads, *song_ids: str):
    store.add([
        PendingDownload(song_id, {'song_id': song_id, 'name': song_id})
        for song_id in song_ids
    ])


def test_queue_controls_require_an_admin(queue_client):
    client, _ = queue_client
    assert client.post('/api/queue/priority', json={}).status_code == 401
    _login(client, 'listener', 'password123')
    assert client.post('/api/queue/priority', json={}).status_code == 403
    assert client.post('/api/queue/bulk', json={}).status_code == 403


def test_priority_changes_only_queued_jobs(queue_client):
    client, store = queue_client
    _login(client)
    _saved(store, 'queued', 'running')
    _job('queued')
    _job('running', status='downloading')

    response = client.post(
        '/api/queue/priority',
        json={'song_ids': ['queued', 'running'], 'priority': 'high'},
    )

    assert response.status_code == 200
    assert response.json()['updated'] == 1
    rows = {row.song_id: row for row in store.rows()}
    assert rows['queued'].priority == 'high'
    assert rows['running'].priority == 'normal'
    assert api.state.download_jobs['queued']['priority'] == 'high'
    assert api.state.download_jobs['running']['priority'] == 'normal'


def test_priority_rejects_unknown_values(queue_client):
    client, store = queue_client
    _login(client)
    _saved(store, 'queued')
    _job('queued')

    response = client.post(
        '/api/queue/priority',
        json={'song_ids': ['queued'], 'priority': 'urgent'},
    )

    assert response.status_code == 400
    assert store.rows()[0].priority == 'normal'


def test_bulk_remove_only_removes_waiting_jobs(queue_client):
    client, store = queue_client
    _login(client)
    _saved(store, 'queued', 'running')
    _job('queued')
    _job('running', status='downloading')
    _job('done', status='done')

    response = client.post(
        '/api/queue/bulk',
        json={
            'action': 'remove',
            'song_ids': ['queued', 'running', 'done', 'missing'],
        },
    )

    assert response.status_code == 200
    assert response.json()['changed'] == 1
    assert 'queued' not in api.state.download_jobs
    assert 'running' in api.state.download_jobs
    assert 'done' in api.state.download_jobs
    assert [row.song_id for row in store.rows()] == ['running']


def test_bulk_pause_and_resume_only_waiting_jobs(queue_client):
    client, store = queue_client
    _login(client)
    _saved(store, 'queued', 'running')
    _job('queued')
    _job('running', status='downloading')

    paused = client.post(
        '/api/queue/bulk',
        json={'action': 'pause', 'song_ids': ['queued', 'running']},
    )
    assert paused.status_code == 200
    assert paused.json()['changed'] == 1
    assert api.state.download_jobs['queued']['status'] == 'paused'
    assert api.state.download_jobs['running']['status'] == 'downloading'
    assert {row.song_id: row for row in store.rows()}['queued'].paused is True

    resumed = client.post(
        '/api/queue/bulk',
        json={'action': 'resume', 'song_ids': ['queued', 'running']},
    )
    assert resumed.status_code == 200
    assert resumed.json()['changed'] == 1
    assert api.state.download_jobs['queued']['status'] == 'queued'
    assert api.state.download_jobs['running']['status'] == 'downloading'
    assert {row.song_id: row for row in store.rows()}['queued'].paused is False


def test_bulk_resume_ignores_a_paused_job_missing_from_storage(queue_client):
    client, store = queue_client
    _login(client)
    _job('paused')
    api.state.download_jobs['paused']['status'] = 'paused'
    queue_pause.pause_job('paused')

    response = client.post(
        '/api/queue/bulk',
        json={'action': 'resume', 'song_ids': ['paused']},
    )

    assert response.status_code == 200
    assert response.json() == {'action': 'resume', 'changed': 0}
    assert 'paused' not in api.state.download_jobs
    assert store.rows() == []


def test_paused_job_stays_paused_after_restart(queue_client, monkeypatch):
    client, store = queue_client
    _login(client)
    _saved(store, 'paused')
    _job('paused')
    assert (
        client.post(
            '/api/queue/bulk',
            json={'action': 'pause', 'song_ids': ['paused']},
        ).status_code
        == 200
    )

    api.state.download_jobs.clear()
    queue_pause.clear_paused_jobs()
    captured = []

    async def fake_run(rows):
        captured.extend(row.song_id for row in rows)

    monkeypatch.setattr(api, '_run_restored_queue', fake_run)

    async def scenario():
        count = await api.restore_download_queue()
        await asyncio.sleep(0)
        return count

    assert asyncio.run(scenario()) == 1
    assert captured == ['paused']
    assert api.state.download_jobs['paused']['status'] == 'paused'
    assert queue_pause.job_paused('paused') is True


def test_paused_job_does_not_take_a_download_slot(monkeypatch):
    class TrackingSemaphore:
        acquired = False

        async def __aenter__(self):
            self.acquired = True
            return self

        async def __aexit__(self, *args):
            self.acquired = False

    class Downloader:
        overwrite_existing_files = True

        @staticmethod
        def download(song, progress, subdir=None):
            return None

    semaphore = TrackingSemaphore()
    monkeypatch.setattr(api.state, 'download_semaphore', semaphore)
    monkeypatch.setattr(api.state, 'downloader', Downloader())
    monkeypatch.setattr(api.state, 'connections', _Connections())
    monkeypatch.setattr(api.state, 'pending_downloads', None)
    song = {'song_id': 'paused', 'name': 'Paused'}
    job_id = api._register_job(song)
    queue_pause.pause_job(job_id)

    async def scenario():
        task = asyncio.create_task(
            api._run_download(song, job_id, pending_saved=True)
        )
        await asyncio.sleep(0)
        try:
            assert semaphore.acquired is False
        finally:
            queue_pause.resume_job(job_id)
            await asyncio.wait_for(task, 1)

    try:
        asyncio.run(scenario())
    finally:
        api.state.download_jobs.clear()
        queue_pause.clear_paused_jobs()


def test_paused_job_waits_before_starting(monkeypatch):
    monkeypatch.setattr(api.state, 'connections', _Connections())
    song = {'song_id': 'paused', 'name': 'Paused'}
    job_id = api._register_job(song)
    job = api.state.download_jobs[job_id]
    queue_pause.pause_job(job_id)

    async def scenario():
        task = asyncio.create_task(api._wait_for_job_resume(job_id, job))
        await asyncio.sleep(0)
        assert not task.done()
        assert job['status'] == 'paused'
        queue_pause.resume_job(job_id)
        return await asyncio.wait_for(task, 1)

    try:
        assert asyncio.run(scenario()) is True
    finally:
        api.state.download_jobs.clear()
        queue_pause.clear_paused_jobs()
