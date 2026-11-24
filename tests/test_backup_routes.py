from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from downtify import api, auth_routes
from downtify.auth import AuthMiddleware, AuthStore
from downtify.backup import BackupStore
from downtify.backup_routes import router as backup_router


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'settings.json').write_text(json.dumps({'format': 'mp3'}))
    store = BackupStore(data)
    monkeypatch.setattr(api.state, 'backup_store', store)
    monkeypatch.setattr(api.state, 'settings_path', data / 'settings.json')
    auth = AuthStore(data / 'downtify.db', data / '.secret')
    auth.users.ensure_default_admin(existing_install=False)
    monkeypatch.setattr(api.state, 'auth', auth)
    app = FastAPI()
    app.add_middleware(
        AuthMiddleware,
        get_store=lambda: auth,
        get_tickets=lambda: None,
    )
    app.include_router(backup_router)
    app.include_router(auth_routes.router)
    return TestClient(app, base_url='http://testserver')


def _login(client):
    response = client.post(
        '/api/auth/login', json={'username': 'admin', 'password': 'downtify'}
    )
    assert response.status_code == 200


def test_backup_routes_require_an_admin(client):
    assert client.get('/api/backups').status_code == 401
    _login(client)
    assert client.get('/api/backups').status_code == 200


def test_create_list_download_and_delete_backup(client):
    _login(client)
    created = client.post('/api/backups')
    assert created.status_code == 200
    item = created.json()
    assert item['name'].startswith('downtify-')
    assert item['name'].endswith('.json.gz')
    assert 'token' not in json.dumps(item)

    listing = client.get('/api/backups').json()
    assert [row['name'] for row in listing['items']] == [item['name']]
    download = client.get(f'/api/backups/{item["name"]}')
    assert download.status_code == 200
    assert json.loads(gzip.decompress(download.content))['version'] == 1

    assert client.delete(f'/api/backups/{item["name"]}').status_code == 200
    assert client.get('/api/backups').json()['items'] == []


def test_restore_requires_dry_run_then_confirmation(client, tmp_path):
    _login(client)
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'settings.json').write_text(json.dumps({'format': 'flac'}))
    backup = BackupStore(source).write()
    target = api.state.backup_store.backup_dir / backup.name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(backup.read_bytes())
    target.chmod(0o600)
    name = backup.name

    assert (
        client.post(
            '/api/backups/restore', json={'name': name, 'dry_run': False}
        ).status_code
        == 400
    )
    assert not (api.state.backup_store.data_dir / 'downloads').exists()

    preview = client.post(
        '/api/backups/restore',
        json={'name': name, 'dry_run': True, 'requeue_missing': True},
    )
    assert preview.status_code == 200
    assert preview.json()['dry_run'] is True
    assert (
        json.loads(
            (api.state.backup_store.data_dir / 'settings.json').read_text()
        )['format']
        == 'mp3'
    )

    restored = client.post(
        '/api/backups/restore',
        json={
            'name': name,
            'dry_run': False,
            'confirm': True,
            'requeue_missing': True,
        },
    )
    assert restored.status_code == 200
    assert restored.json()['dry_run'] is False
    assert (
        json.loads(
            (api.state.backup_store.data_dir / 'settings.json').read_text()
        )['format']
        == 'flac'
    )


def test_backup_routes_reject_path_traversal(client):
    _login(client)
    for name in ('../settings.json', '/etc/passwd', 'other.json.gz'):
        assert client.get(f'/api/backups/{name}').status_code in {400, 404}
        assert client.delete(f'/api/backups/{name}').status_code in {400, 404}


def test_upload_preview_and_restore_an_uploaded_backup(client):
    _login(client)
    source = BackupStore(api.state.backup_store.data_dir)
    backup = source.write()
    content = backup.read_bytes()
    backup.unlink()

    uploaded = client.post(
        '/api/backups/upload',
        files={'file': (backup.name, content, 'application/gzip')},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()['name'] == backup.name
    assert client.get('/api/backups').json()['items'][0]['name'] == backup.name
