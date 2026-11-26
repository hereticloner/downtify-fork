import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from downtify import spotify_context
from downtify.listening_history import ListeningStore


class FakeResponse:
    def __init__(self, body=None, status=200, headers=None):
        self._body = body if body is not None else {}
        self.status_code = status
        self.headers = headers or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f'HTTP {self.status_code}')


def _settings(**overrides):
    block = {
        'enabled': True,
        'client_id': 'client',
        'access_token': 'access',
        'refresh_token': 'refresh',
        'token_expires_at': 99999999999,
        'import_recent': False,
    }
    block.update(overrides)
    return {'spotify_mirror': block}


def _seed(db, *, played_at='2026-11-20T20:15:00Z', key='abc'):
    spotify_context.ensure_schema(db)
    store = ListeningStore(db)
    store.link_or_create(
        user_id=1,
        source='spotify',
        source_key=f'spotify:{key}',
        played_at=played_at,
        artist='Artist',
        title=f'Title {key}',
        context=f'spotify:playlist:{key}',
        context_type='playlist',
    )


def _success_request(calls):
    def request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return FakeResponse({'name': 'Real Playlist'})

    return request


def test_resolver_uses_existing_token_and_caches_name(tmp_path, monkeypatch):
    db = tmp_path / 'activity.db'
    _seed(db)
    calls = []
    monkeypatch.setattr(spotify_context.time, 'sleep', lambda _seconds: None)

    summary = spotify_context.run_once(
        _settings(), db, request=_success_request(calls)
    )

    assert summary['resolved'] == 1
    assert calls[0][1].endswith('/v1/playlists/abc')
    assert spotify_context.labels_for(db, ['spotify:playlist:abc']) == {
        'spotify:playlist:abc': 'Real Playlist'
    }


def test_resolver_processes_oldest_context_first(tmp_path, monkeypatch):
    db = tmp_path / 'activity.db'
    _seed(db, played_at='2026-11-18T20:15:00Z', key='old')
    _seed(db, played_at='2026-11-20T20:15:00Z', key='new')
    calls = []
    monkeypatch.setattr(spotify_context.time, 'sleep', lambda _seconds: None)

    spotify_context.run_once(
        _settings(), db, limit=1, request=_success_request(calls)
    )

    assert len(calls) == 1
    assert calls[0][1].endswith('/v1/playlists/old')


def test_resolver_refreshes_stale_successful_name(tmp_path, monkeypatch):
    db = tmp_path / 'activity.db'
    _seed(db)
    spotify_context.cache_name(db, 'spotify:playlist:abc', 'Old Name')
    old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    with sqlite3.connect(db) as conn:
        conn.execute('UPDATE spotify_context_cache SET fetched_at=?', (old,))
    calls = []
    monkeypatch.setattr(spotify_context.time, 'sleep', lambda _seconds: None)

    summary = spotify_context.run_once(
        _settings(), db, request=_success_request(calls)
    )

    assert summary['resolved'] == 1
    assert spotify_context.labels_for(db, ['spotify:playlist:abc']) == {
        'spotify:playlist:abc': 'Real Playlist'
    }


def test_resolver_stops_on_429_and_honors_retry_after(tmp_path, monkeypatch):
    db = tmp_path / 'activity.db'
    _seed(db)
    monkeypatch.setattr(spotify_context.time, 'sleep', lambda _seconds: None)

    def rate_limited(method, url, **kwargs):
        return FakeResponse({}, status=429, headers={'Retry-After': '12'})

    summary = spotify_context.run_once(_settings(), db, request=rate_limited)

    assert summary['rate_limited'] is True
    assert summary['retry_after'] == 12
    with sqlite3.connect(db) as conn:
        retry_at = conn.execute(
            'SELECT retry_at FROM spotify_context_cache'
        ).fetchone()[0]
    assert datetime.fromisoformat(retry_at) > datetime.now(timezone.utc)


@pytest.mark.parametrize('status', [401, 403, 404, 500])
def test_resolver_records_http_failure_without_caching_name(
    tmp_path, monkeypatch, status
):
    db = tmp_path / 'activity.db'
    _seed(db)
    monkeypatch.setattr(spotify_context.time, 'sleep', lambda _seconds: None)

    def failed(method, url, **kwargs):
        return FakeResponse({}, status=status)

    summary = spotify_context.run_once(_settings(), db, request=failed)

    assert summary['resolved'] == 0
    assert summary['failed'] == 1
    assert spotify_context.labels_for(db, ['spotify:playlist:abc']) == {}
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            'SELECT last_error, retry_at FROM spotify_context_cache'
        ).fetchone()
    assert row[0]
    assert row[1]


def test_resolver_survives_malformed_json(tmp_path, monkeypatch):
    db = tmp_path / 'activity.db'
    _seed(db)
    monkeypatch.setattr(spotify_context.time, 'sleep', lambda _seconds: None)

    def malformed(method, url, **kwargs):
        response = FakeResponse()
        response.json = lambda: []
        return response

    summary = spotify_context.run_once(_settings(), db, request=malformed)

    assert summary['resolved'] == 0
    assert summary['failed'] == 1


def test_resolver_returns_renewed_tokens_for_persistence(
    tmp_path, monkeypatch
):
    db = tmp_path / 'activity.db'
    _seed(db)
    monkeypatch.setattr(spotify_context.time, 'sleep', lambda _seconds: None)

    def request(method, url, **kwargs):
        if url.endswith('/api/token'):
            return FakeResponse({
                'access_token': 'renewed',
                'refresh_token': 'refresh-2',
                'expires_in': 3600,
            })
        return FakeResponse({'name': 'Real Playlist'})

    summary = spotify_context.run_once(
        _settings(token_expires_at=0), db, request=request
    )

    assert summary['tokens']['access_token'] == 'renewed'
    assert summary['tokens']['refresh_token'] == 'refresh-2'


def test_resolver_is_off_without_enabled_usable_mirror(tmp_path):
    db = tmp_path / 'activity.db'
    _seed(db)

    summary = spotify_context.run_once(
        {'spotify_mirror': {'enabled': False, 'client_id': 'client'}}, db
    )

    assert summary['enabled'] is False
    assert summary['resolved'] == 0


@pytest.mark.asyncio
async def test_loop_persists_renewed_tokens(tmp_path, monkeypatch):
    db = tmp_path / 'activity.db'
    _seed(db)
    saved = []
    monkeypatch.setattr(spotify_context.time, 'sleep', lambda _seconds: None)

    def request(method, url, **kwargs):
        if url.endswith('/api/token'):
            return FakeResponse({
                'access_token': 'renewed',
                'refresh_token': 'refresh-2',
                'expires_in': 3600,
            })
        return FakeResponse({'name': 'Real Playlist'})

    async def stop(_delay):
        raise asyncio.CancelledError

    monkeypatch.setattr(spotify_context.asyncio, 'sleep', stop)
    with pytest.raises(asyncio.CancelledError):
        await spotify_context.spotify_context_loop(
            lambda: _settings(token_expires_at=0),
            db,
            request=request,
            persist_tokens=saved.append,
        )

    assert saved[0]['access_token'] == 'renewed'
