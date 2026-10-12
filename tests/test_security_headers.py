"""Baseline security headers on every response (downtify/security_headers.py)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from starlette.testclient import TestClient

import main
from downtify import api
from downtify.security_headers import HEADERS, SecurityHeadersMiddleware


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
    return TestClient(main.build_app(), base_url='http://testserver')


def test_health_response_carries_the_headers(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    for header, value in HEADERS:
        assert response.headers[header] == value


def test_a_rejected_request_carries_them_too(client):
    """The auth middleware's own 401 is not exempt from them."""

    response = client.get('/api/settings')
    assert response.status_code == 401
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert (
        response.headers['Content-Security-Policy'] == "frame-ancestors 'none'"
    )


def test_a_route_can_set_its_own_value():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get('/own')
    def own() -> PlainTextResponse:
        return PlainTextResponse(
            'ok', headers={'X-Frame-Options': 'SAMEORIGIN'}
        )

    response = TestClient(app).get('/own')
    assert response.headers['X-Frame-Options'] == 'SAMEORIGIN'
    assert response.headers['Referrer-Policy'] == (
        'strict-origin-when-cross-origin'
    )
