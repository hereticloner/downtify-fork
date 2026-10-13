"""Tests for the Spotify listening-history import (downtify.spotify_history).

Every HTTP call is injected, so nothing touches the network; the
assertions are about what the endpoint's body turns into, how the store
dedupes, what the switch does to the loop and what the reader returns.
"""

from __future__ import annotations

import asyncio
import sqlite3
import threading
from pathlib import Path

from downtify import spotify_history
from downtify.spotify_history import (
    clamp_limit,
    fetch_recently_played,
    get_recent_from_spotify,
    import_enabled,
    parse_plays,
    run_once,
    save_recently_played,
    spotify_history_loop,
)

#: How long a loop test waits before it gives up on its condition.
_LOOP_TURNS = 600
_LOOP_POLL = 0.01


class FakeResponse:
    def __init__(
        self, body=None, status_code: int = 200, headers=None
    ) -> None:
        self._body = body if body is not None else {}
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f'HTTP {self.status_code}')

    def json(self):
        return self._body


def _config(**overrides):
    """A mirror config with a token that needs no refresh."""

    config = {
        'client_id': 'cid',
        'access_token': 'at',
        'refresh_token': 'rt',
        'device_id': 'dev-1',
        'token_expires_at': 99999999999,
    }
    config.update(overrides)
    return config


def _settings(**mirror):
    block = {
        'enabled': True,
        'client_id': 'cid',
        'access_token': 'at',
        'refresh_token': 'rt',
        'token_expires_at': 99999999999,
        'import_recent': True,
    }
    block.update(mirror)
    return {'spotify_mirror': block}


def _play(played_at='2026-10-13T10:00:00.000Z', tid='t1', synced_at=''):
    return {
        'played_at': played_at,
        'track_name': 'Song',
        'artist_name': 'Artist',
        'album_name': 'Album',
        'spotify_track_id': tid,
        'duration_ms': 201000,
        'synced_at': synced_at,
    }


def _history_request(
    calls, body=None, status=200, headers=None, token_body=None
):
    """A request fake: token POSTs, then one recently-played GET."""

    response_headers = headers

    def request(method, url, *, headers=None, params=None, data=None):
        calls.append({
            'method': method,
            'url': url,
            'params': params or {},
            'headers': headers or {},
        })
        if 'api/token' in url:
            return FakeResponse(
                token_body or {'access_token': 'at-new', 'expires_in': 3600},
                200,
            )
        return FakeResponse(
            body if body is not None else {}, status, headers=response_headers
        )

    return request


# ── the switch ───────────────────────────────────────────────────────


def test_import_needs_the_mirror_and_the_flag():
    assert import_enabled(_settings()) is True
    assert import_enabled(_settings(enabled=False)) is False
    assert import_enabled(_settings(import_recent=False)) is False
    assert import_enabled({}) is False
    assert import_enabled(None) is False


def test_clamp_limit_bounds():
    assert clamp_limit(10) == 10
    assert clamp_limit(500) == spotify_history.MAX_LIMIT
    assert clamp_limit(0) == 1
    assert clamp_limit('junk') == spotify_history.DEFAULT_LIMIT


# ── parse_plays ──────────────────────────────────────────────────────


def test_parse_plays_reads_the_endpoint_shape():
    body = {
        'items': [
            {
                'played_at': '2026-10-13T10:00:00.000Z',
                'track': {
                    'id': 't1',
                    'name': 'Song',
                    'duration_ms': 201000,
                    'artists': [{'name': 'A'}, {'name': 'B'}],
                    'album': {'name': 'Album'},
                },
            }
        ]
    }
    assert parse_plays(body) == [
        {
            'played_at': '2026-10-13T10:00:00.000Z',
            'track_name': 'Song',
            'artist_name': 'A, B',
            'album_name': 'Album',
            'spotify_track_id': 't1',
            'duration_ms': 201000,
        }
    ]


def test_parse_plays_reads_the_item_wrapper_and_junk():
    body = {
        'items': [
            {'item': {'id': 'x'}, 'played_at': '2026-10-13T09:00:00.000Z'},
            'not-a-dict',
            {'played_at': '2026-10-13T08:00:00.000Z'},
            {'track': {'id': 'y'}},
            'nope',
        ]
    }
    rows = parse_plays(body)
    assert len(rows) == 1
    assert rows[0]['spotify_track_id'] == 'x'
    # No artists/album in the payload: blank rather than a crash.
    assert not rows[0]['artist_name']
    assert not rows[0]['album_name']


def test_parse_plays_of_a_body_that_is_not_one():
    assert parse_plays(None) == []
    assert parse_plays({'items': 'nope'}) == []


# ── fetch_recently_played ────────────────────────────────────────────


def test_fetch_calls_the_endpoint_with_the_token():
    calls = []
    body = {'items': [{'played_at': 'p', 'track': {'id': 't1'}}]}
    rows = fetch_recently_played(
        _config(), request=_history_request(calls, body), limit=25
    )
    assert [r['spotify_track_id'] for r in rows] == ['t1']
    assert calls[0]['url'].endswith('/me/player/recently-played')
    assert calls[0]['params'] == {'limit': 25}
    assert calls[0]['headers']['Authorization'] == 'Bearer at'


def test_fetch_refreshes_a_stale_token_and_writes_it_back():
    calls = []
    config = _config(token_expires_at=0)
    body = {'items': [{'played_at': 'p', 'track': {'id': 't1'}}]}
    rows = fetch_recently_played(config, request=_history_request(calls, body))
    assert len(rows) == 1
    assert config['access_token'] == 'at-new'
    assert calls[0]['url'].endswith('/api/token')
    assert calls[1]['headers']['Authorization'] == 'Bearer at-new'


def test_fetch_none_when_the_token_cannot_renew():
    calls = []
    config = _config(token_expires_at=0, refresh_token='')
    assert (
        fetch_recently_played(config, request=_history_request(calls)) is None
    )
    assert not [c for c in calls if 'recently-played' in c['url']]


def test_fetch_none_on_an_http_error():
    calls = []
    assert (
        fetch_recently_played(
            _config(),
            request=_history_request(calls, status=500),
        )
        is None
    )


def test_fetch_none_when_the_scope_was_never_granted():
    calls = []
    assert (
        fetch_recently_played(
            _config(), request=_history_request(calls, status=403)
        )
        is None
    )


def test_fetch_waits_out_a_429(monkeypatch):
    calls = []
    slept: list[float] = []
    monkeypatch.setattr(spotify_history.time, 'sleep', slept.append)
    rows = fetch_recently_played(
        _config(),
        request=_history_request(
            calls, status=429, headers={'Retry-After': '12'}
        ),
    )
    assert rows is None
    assert slept == [12.0]


def test_fetch_gives_up_on_a_429_without_a_usable_header(monkeypatch):
    calls = []
    slept: list[float] = []
    monkeypatch.setattr(spotify_history.time, 'sleep', slept.append)
    assert (
        fetch_recently_played(
            _config(), request=_history_request(calls, status=429)
        )
        is None
    )
    assert slept == [spotify_history.MAX_BACKOFF_SECONDS]


# ── the store ────────────────────────────────────────────────────────


def test_save_writes_and_the_reader_reads_it_back(tmp_path: Path):
    db = tmp_path / 'activity.db'
    assert (
        save_recently_played(
            db, [_play(), _play('2026-10-13T09:00:00.000Z', 't0')]
        )
        == 2
    )

    rows = get_recent_from_spotify(db)
    assert [r['spotify_track_id'] for r in rows] == ['t1', 't0']
    assert rows[0]['track_name'] == 'Song'
    assert rows[0]['duration_ms'] == 201000
    assert rows[0]['synced_at']
    assert spotify_history.count_plays(db) == 2


def test_save_ignores_a_play_it_already_has(tmp_path: Path):
    db = tmp_path / 'activity.db'
    assert save_recently_played(db, [_play()]) == 1
    # The endpoint's windows overlap: the same play comes back next pass.
    assert (
        save_recently_played(
            db, [_play(), _play('2026-10-13T11:00:00.000Z', 't2')]
        )
        == 1
    )
    assert spotify_history.count_plays(db) == 2


def test_save_drops_rows_without_a_key_and_stamps_synced_at(tmp_path: Path):
    db = tmp_path / 'activity.db'
    assert (
        save_recently_played(
            db,
            [
                {'track_name': 'no key'},
                'junk',
                _play(synced_at='2026-10-13T12:00:00.000Z'),
            ],
        )
        == 1
    )
    rows = get_recent_from_spotify(db)
    assert rows[0]['synced_at'] == '2026-10-13T12:00:00.000Z'


def test_save_of_nothing_creates_nothing(tmp_path: Path):
    db = tmp_path / 'activity.db'
    assert save_recently_played(db, []) == 0
    assert not db.exists()


def test_save_a_bad_duration_reads_back_as_zero(tmp_path: Path):
    db = tmp_path / 'activity.db'
    row = _play()
    row['duration_ms'] = 'not-a-number'
    save_recently_played(db, [row])
    assert get_recent_from_spotify(db)[0]['duration_ms'] == 0


def test_reader_limits_and_orders_newest_first(tmp_path: Path):
    db = tmp_path / 'activity.db'
    save_recently_played(
        db,
        [
            _play(f'2026-10-13T0{hour}:00:00.000Z', f't{hour}')
            for hour in range(5)
        ],
    )
    rows = get_recent_from_spotify(db, limit=2)
    assert [r['spotify_track_id'] for r in rows] == ['t4', 't3']


def test_reader_of_a_database_that_is_not_there(tmp_path: Path):
    assert get_recent_from_spotify(tmp_path / 'missing.db') == []
    assert not (tmp_path / 'missing.db').exists()


def test_reader_of_a_database_without_the_table(tmp_path: Path):
    db = tmp_path / 'activity.db'
    with sqlite3.connect(str(db)) as conn:
        conn.execute('CREATE TABLE something_else (a TEXT)')
    assert get_recent_from_spotify(db) == []


# ── one sweep ────────────────────────────────────────────────────────


def test_run_once_stores_what_it_reads(tmp_path: Path):
    calls = []
    db = tmp_path / 'activity.db'
    summary = run_once(
        _settings(),
        db,
        request=_history_request(
            calls, {'items': [{'played_at': 'p', 'track': {'id': 't1'}}]}
        ),
    )
    assert summary['enabled'] is True
    assert summary['fetched'] == 1
    assert summary['saved'] == 1
    assert not summary['error']
    assert spotify_history.count_plays(db) == 1


def test_run_once_while_the_switch_is_off(tmp_path: Path):
    calls = []
    db = tmp_path / 'activity.db'
    summary = run_once(
        _settings(import_recent=False), db, request=_history_request(calls)
    )
    assert summary['enabled'] is False
    assert calls == []
    assert not db.exists()


def test_run_once_hands_back_a_renewed_token(tmp_path: Path):
    calls = []
    settings = _settings(
        access_token='at', refresh_token='rt', token_expires_at=0
    )
    summary = run_once(
        settings,
        tmp_path / 'activity.db',
        request=_history_request(calls, {'items': []}),
    )
    assert summary['tokens']['access_token'] == 'at-new'


def test_run_once_reports_a_failed_fetch(tmp_path: Path):
    calls = []
    summary = run_once(
        _settings(),
        tmp_path / 'activity.db',
        request=_history_request(calls, status=403),
    )
    assert summary['error'] == 'fetch_failed'
    assert summary['saved'] == 0


# ── the periodic loop ────────────────────────────────────────────────


def _run_loop(loop, until: threading.Event, turns: int = 1) -> None:
    """Run *loop* until *until* is set (or it has taken *turns* passes)."""

    async def run():
        task = asyncio.create_task(loop)
        for _ in range(_LOOP_TURNS * (turns + 1)):
            if until.is_set():
                break
            await asyncio.sleep(_LOOP_POLL)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(run())


def _settings_getter(settings, until: threading.Event, turns: int = 3):
    """A ``cfg_getter`` that signals once the loop has passed *turns* times."""

    seen = {'n': 0}

    def get_settings():
        seen['n'] += 1
        if seen['n'] >= turns:
            until.set()
        return settings

    return get_settings


def test_loop_fetches_nothing_while_disabled(tmp_path: Path):
    calls = []
    db = tmp_path / 'activity.db'
    until = threading.Event()
    _run_loop(
        spotify_history_loop(
            cfg_getter=_settings_getter(_settings(import_recent=False), until),
            db_path=db,
            idle_seconds=0,
            request=_history_request(calls),
        ),
        until,
    )
    assert until.is_set(), 'the loop never woke up'
    assert calls == []
    assert not db.exists()


def test_loop_fetches_nothing_without_a_client_id(tmp_path: Path):
    calls = []
    db = tmp_path / 'activity.db'
    until = threading.Event()
    _run_loop(
        spotify_history_loop(
            cfg_getter=_settings_getter(
                {'spotify_mirror': {'enabled': True, 'import_recent': True}},
                until,
            ),
            db_path=db,
            idle_seconds=0,
            request=_history_request(calls),
        ),
        until,
    )
    assert calls == []
    assert spotify_history.count_plays(db) == 0


def test_loop_stores_plays_and_persists_a_renewal(tmp_path: Path):
    calls = []
    saved: list[dict] = []
    db = tmp_path / 'activity.db'
    until = threading.Event()
    settings = _settings(token_expires_at=0)

    def persist(tokens):
        saved.append(tokens)
        until.set()

    _run_loop(
        spotify_history_loop(
            cfg_getter=lambda: settings,
            db_path=db,
            idle_seconds=0,
            request=_history_request(
                calls,
                {'items': [{'played_at': 'p', 'track': {'id': 't1'}}]},
            ),
            persist_tokens=persist,
        ),
        until,
    )
    assert until.is_set(), 'the sweep never finished'
    assert saved[0]['access_token'] == 'at-new'
    assert [r['spotify_track_id'] for r in get_recent_from_spotify(db)] == [
        't1'
    ]


def test_loop_survives_a_broken_settings_getter(tmp_path: Path):
    until = threading.Event()
    seen = {'n': 0}

    def boom():
        seen['n'] += 1
        if seen['n'] >= 3:
            until.set()
        raise RuntimeError('settings exploded')

    _run_loop(
        spotify_history_loop(
            cfg_getter=boom,
            db_path=tmp_path / 'activity.db',
            idle_seconds=0,
        ),
        until,
    )
    assert until.is_set(), 'the loop died on the first failure'
