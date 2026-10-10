"""User-facing HTTP errors carry a machine-readable ``code`` next to the
human ``detail`` (downtify/errors.py + main.py's handler). The web UI
translates ``code`` (frontend/src/lib/errors.js) instead of showing the
English text."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.testclient import TestClient

import main
from downtify import api
from downtify.errors import STATUS_CODES, ApiError, code_for


def test_api_error_keeps_detail_and_adds_code():
    exc = ApiError(
        401, 'auth.invalid_credentials', 'Wrong username or password'
    )
    assert exc.status_code == 401
    assert exc.detail == 'Wrong username or password'
    assert exc.code == 'auth.invalid_credentials'
    assert code_for(exc) == 'auth.invalid_credentials'


def test_code_for_falls_back_to_the_status():
    assert code_for(HTTPException(status_code=404)) == 'resource.not_found'
    assert (
        code_for(StarletteHTTPException(status_code=503)) == 'server.starting'
    )
    assert code_for(HTTPException(status_code=400)) == 'request.invalid'


def test_code_for_defaults_to_server_error():
    assert code_for(HTTPException(status_code=418)) == 'server.error'


def test_status_codes_are_lowercase_dotted():
    for code in STATUS_CODES.values():
        assert code == code.lower()
        assert '.' in code


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A built app (no lifespan) whose error handler we can exercise."""

    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html>Downtify</html>')
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', tmp_path / 'downloads')
    monkeypatch.setattr(main, 'DATABASE_DIR', tmp_path / 'data')
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))
    for name in ('auth', 'activity', 'identity', 'downloader', 'settings'):
        monkeypatch.setattr(api.state, name, getattr(api.state, name))
    return TestClient(main.build_app(), base_url='http://testserver')


def test_login_refusal_returns_a_code(client):
    response = client.post(
        '/api/auth/login',
        json={'username': 'admin', 'password': 'definitely-wrong'},
    )
    assert response.status_code == 401
    body = response.json()
    assert body['code'] == 'auth.invalid_credentials'
    # The English detail is preserved for API clients.
    assert body['detail'] == 'Wrong username or password'


def test_error_response_still_has_a_detail(client):
    """Adding the code must not drop or reshape ``detail``."""

    response = client.post('/api/auth/login', json={})
    # The route requires credentials; whatever the outcome, the shape holds.
    body = response.json()
    assert 'code' in body
    assert 'detail' in body
