"""Tests for the Spotify live sync (downtify.spotify_sync).

Every HTTP call is injected, so nothing touches the network; the
assertions are about the snapshot diff, the due/interval gate, the
token-refresh contract and the "nothing changed -> nothing done" rule.
"""

from __future__ import annotations

import asyncio
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from fastapi import HTTPException

from downtify import api, spotify_sync
from downtify.spotify_sync import (
    DEFAULT_INTERVAL_MINUTES,
    MAX_INTERVAL_MINUTES,
    MIN_INTERVAL_MINUTES,
    SyncSnapshotStore,
    apply_removals,
    clean_settings,
    is_due,
    normalize_snapshot,
    run_sync,
    snapshot_diff,
)


class FakeResponse:
    def __init__(
        self, body=None, status_code: int = 200, headers=None
    ) -> None:
        self._body = body if body is not None else {}
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            # The shape production raises: the code reads status and
            # Retry-After off ``exc.response``.
            raise httpx.HTTPStatusError(
                f'HTTP {self.status_code}',
                request=httpx.Request('GET', 'https://example.test'),
                response=httpx.Response(
                    self.status_code,
                    headers=self.headers,
                    request=httpx.Request('GET', 'https://example.test'),
                ),
            )

    def json(self):
        return self._body


@pytest.fixture(autouse=True)
def _no_rate_limit_cooldown():
    """The refusal cooldown is process state; don't leak it between tests."""

    spotify_sync._RATE_LIMITED_UNTIL.clear()
    yield
    spotify_sync._RATE_LIMITED_UNTIL.clear()


def _config(**overrides):
    config = {
        'client_id': 'cid',
        'access_token': 'at',
        'refresh_token': 'rt',
        'device_id': 'dev-1',
        'token_expires_at': 99999999999,
        'silent_on_target': True,
    }
    config.update(overrides)
    return config


def _track_pages(pages, calls, token_body=None, status=200, snapshot_id=''):
    """A request fake: token POSTs, the playlist metadata, then the pages.

    *snapshot_id* is what ``GET /playlists/{id}`` answers with; the empty
    default stands for "no metadata available", which is the case every
    pre-snapshot-check test was written against.
    """

    seen = {'page': 0}

    def request(  # noqa: PLR0913, PLR0917
        method, url, *, headers=None, params=None, json=None, data=None
    ):
        calls.append({
            'method': method,
            'url': url,
            'params': params or {},
            'headers': headers or {},
        })
        if 'api/token' in url:
            body = token_body or {
                'access_token': 'at-new',
                'expires_in': 3600,
            }
            return FakeResponse(body, 200)
        if status >= 400:
            return FakeResponse({}, status)
        if '/playlists/' in url and '/tracks' not in url:
            return FakeResponse({'snapshot_id': snapshot_id}, 200)
        index = seen['page']
        seen['page'] += 1
        body = pages[index] if index < len(pages) else {'items': []}
        return FakeResponse(body, 200)

    return request


def _page(ids, *, next_url=''):
    return {
        'items': [{'track': {'id': tid}} for tid in ids],
        'next': next_url,
    }


# ── normalize_snapshot ───────────────────────────────────────────────


def test_normalize_accepts_dicts_and_strings():
    assert normalize_snapshot([
        {'song_id': 'a'},
        {'id': 'b'},
        {'uri': 'spotify:track:c'},
        'd',
    ]) == ['a', 'b', 'c', 'd']


def test_normalize_dedupes_and_keeps_order():
    assert normalize_snapshot(['b', 'a', 'b', 'a']) == ['b', 'a']


def test_normalize_ignores_junk():
    assert normalize_snapshot(None) == []
    assert normalize_snapshot([None, {}, {'name': 'x'}, '']) == []


# ── snapshot_diff ────────────────────────────────────────────────────


def test_diff_detects_additions():
    diff = snapshot_diff(['a', 'b'], ['a', 'b', 'c', 'd'])
    assert diff['added'] == ['c', 'd']
    assert diff['removed'] == []
    assert diff['changed'] is True


def test_diff_detects_removals():
    diff = snapshot_diff(['a', 'b', 'c'], ['a'])
    assert diff['added'] == []
    assert diff['removed'] == ['b', 'c']
    assert diff['changed'] is True


def test_diff_no_change():
    diff = snapshot_diff(['a', 'b'], ['a', 'b'])
    assert diff == {'added': [], 'removed': [], 'changed': False}


def test_diff_a_reorder_is_not_a_change():
    diff = snapshot_diff(['a', 'b'], ['b', 'a'])
    assert diff['changed'] is False


def test_diff_first_snapshot_is_all_new():
    diff = snapshot_diff([], ['a', 'b'])
    assert diff['added'] == ['a', 'b']
    assert diff['changed'] is True


# ── interval / due ───────────────────────────────────────────────────


def test_default_interval_is_sane():
    assert MIN_INTERVAL_MINUTES <= DEFAULT_INTERVAL_MINUTES
    assert DEFAULT_INTERVAL_MINUTES <= MAX_INTERVAL_MINUTES


def test_clamp_interval_bounds():
    assert clean_settings({'interval_minutes': 0})['interval_minutes'] == (
        MIN_INTERVAL_MINUTES
    )
    assert (
        clean_settings({'interval_minutes': 10**9})['interval_minutes']
        == MAX_INTERVAL_MINUTES
    )
    assert (
        clean_settings({'interval_minutes': 'oops'})['interval_minutes']
        == DEFAULT_INTERVAL_MINUTES
    )


def test_default_settings_off():
    assert clean_settings(None) == {
        'enabled': False,
        'interval_minutes': DEFAULT_INTERVAL_MINUTES,
    }


def test_is_due_without_a_stamp():
    assert is_due(None, 60) is True
    assert is_due('not a date', 60) is True


def test_is_due_respects_the_interval():
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    recent = (now - timedelta(minutes=10)).isoformat()
    stale = (now - timedelta(minutes=120)).isoformat()
    assert is_due(recent, 60, now=now) is False
    assert is_due(stale, 60, now=now) is True


# ── the snapshot store ───────────────────────────────────────────────


def test_store_round_trip(tmp_path: Path):
    store = SyncSnapshotStore(tmp_path / 'sync.json')
    assert store.track_ids('p1') is None
    store.save('p1', ['a', 'b'], name='Mix')
    assert store.track_ids('p1') == ['a', 'b']
    assert store.synced_at('p1')
    store.save('p1', ['a', 'b', 'c'], name='Mix')
    assert store.track_ids('p1') == ['a', 'b', 'c']
    assert store.forget('p1') is True
    assert store.track_ids('p1') is None
    assert store.forget('p1') is False


def test_store_survives_a_broken_file(tmp_path: Path):
    path = tmp_path / 'sync.json'
    path.write_text('{ not json', encoding='utf-8')
    store = SyncSnapshotStore(path)
    assert store.all() == {}
    store.save('p1', ['a'])
    assert store.track_ids('p1') == ['a']


def test_a_failed_write_keeps_the_previous_file(tmp_path: Path, monkeypatch):
    """A write that cannot finish must not truncate what is already stored."""

    path = tmp_path / 'sync.json'
    store = SyncSnapshotStore(path)
    store.save('p1', ['a'], name='Mix')
    before = path.read_text(encoding='utf-8')

    def boom(*_args, **_kwargs):
        raise OSError('disk went away')

    monkeypatch.setattr(spotify_sync.os, 'replace', boom)
    with pytest.raises(OSError, match='disk went away'):
        store.save('p1', ['a', 'b'])

    assert path.read_text(encoding='utf-8') == before
    assert store.track_ids('p1') == ['a']
    assert list(tmp_path.glob('*.tmp')) == []


def test_a_write_leaves_no_temporary_file_behind(tmp_path: Path):
    path = tmp_path / 'sync.json'
    store = SyncSnapshotStore(path)
    store.save('p1', ['a'])
    store.save('p2', ['b'])
    store.forget('p1')
    assert list(tmp_path.glob('*.tmp')) == []
    assert sorted(store.all()) == ['p2']


def test_concurrent_writers_do_not_lose_entries(tmp_path: Path, monkeypatch):
    """The periodic loop and a manual "Sync now" write the same file.

    Every save is a read-modify-write of the whole map, so without the lock
    the slower writer's entry disappears. ``_write`` is slowed here so the
    writers are all inside their read-modify-write at the same time.
    """

    path = tmp_path / 'sync.json'
    store = SyncSnapshotStore(path)
    real_write = SyncSnapshotStore._write

    def slow_write(self, data):
        time.sleep(0.05)
        real_write(self, data)

    monkeypatch.setattr(SyncSnapshotStore, '_write', slow_write)

    def save(playlist_id: str, track: str) -> None:
        store.save(playlist_id, [track], name=playlist_id)

    threads = [
        threading.Thread(target=save, args=(f'p{i}', f't{i}'))
        for i in range(4)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(store.all()) == ['p0', 'p1', 'p2', 'p3']
    assert store.track_ids('p3') == ['t3']


# ── fetch_snapshot (OAuth) ───────────────────────────────────────────


def test_fetch_snapshot_pages_through_next():
    calls = []
    pages = [
        _page(['a', 'b'], next_url='https://api.spotify.com/next'),
        _page(['c']),
    ]
    ids = spotify_sync.fetch_snapshot(
        _config(), 'pl', request=_track_pages(pages, calls)
    )
    assert ids == ['a', 'b', 'c']
    assert calls[0]['headers']['Authorization'] == 'Bearer at'


def test_fetch_snapshot_refreshes_a_stale_token():
    calls = []
    config = _config(token_expires_at=0)
    ids = spotify_sync.fetch_snapshot(
        config,
        'pl',
        request=_track_pages([_page(['a'])], calls),
    )
    assert ids == ['a']
    # ensure_token renewed it and fetch wrote the new token back.
    assert config['access_token'] == 'at-new'
    assert calls[0]['url'].endswith('/api/token')
    assert calls[1]['headers']['Authorization'] == 'Bearer at-new'


def test_fetch_snapshot_reads_both_row_wrappers():
    calls = []
    page = {
        'items': [{'item': {'id': 'x'}}, {'track': {'id': 'y'}}],
        'next': '',
    }
    ids = spotify_sync.fetch_snapshot(
        _config(), 'pl', request=_track_pages([page], calls)
    )
    assert ids == ['x', 'y']


def test_fetch_snapshot_none_when_token_cannot_renew():
    calls = []
    config = _config(token_expires_at=0, refresh_token='')
    assert (
        spotify_sync.fetch_snapshot(
            config, 'pl', request=_track_pages([], calls)
        )
        is None
    )
    # No playlist call went out once the token failed.
    assert not [c for c in calls if '/tracks' in c['url']]


def test_fetch_snapshot_none_on_http_error():
    calls = []
    assert (
        spotify_sync.fetch_snapshot(
            _config(),
            'pl',
            request=_track_pages([_page(['a'])], calls, status=403),
        )
        is None
    )


def test_fetch_snapshot_none_for_an_empty_id():
    assert spotify_sync.fetch_snapshot(_config(), '') is None


# ── sync_playlist ────────────────────────────────────────────────────


# ── the cheap "did anything change?" check ───────────────────────────


def test_unchanged_snapshot_never_reads_the_quota_bound_tracks(tmp_path: Path):
    """/playlists/{id}/tracks is the endpoint that runs out of quota."""

    store = SyncSnapshotStore(tmp_path / 'sync.json')
    store.save('pl', ['a'], snapshot_id='snap-1')
    calls = []
    result = spotify_sync.sync_playlist(
        _playlist(),
        config=_config(),
        store=store,
        apply=lambda n, a, r: None,
        request=_track_pages([_page(['a', 'b'])], calls, snapshot_id='snap-1'),
    )

    assert result['skipped'] == 'unchanged'
    assert result['changed'] is False
    assert not [c for c in calls if c['url'].endswith('/tracks')]


def test_a_new_snapshot_reads_the_tracks_and_applies(tmp_path: Path):
    store = SyncSnapshotStore(tmp_path / 'sync.json')
    store.save('pl', ['a'], snapshot_id='snap-1')
    applied = []
    calls = []
    result = spotify_sync.sync_playlist(
        _playlist(),
        config=_config(),
        store=store,
        apply=lambda n, a, r: applied.append((n, a, r)),
        request=_track_pages([_page(['a', 'b'])], calls, snapshot_id='snap-2'),
    )

    assert result['changed'] is True
    assert result['added'] == ['b']
    assert applied
    assert store.snapshot_id('pl') == 'snap-2'


def test_the_first_sync_reads_the_tracks_and_records_the_snapshot(
    tmp_path: Path,
):
    store = SyncSnapshotStore(tmp_path / 'sync.json')
    calls = []
    result = spotify_sync.sync_playlist(
        _playlist(),
        config=_config(),
        store=store,
        apply=lambda n, a, r: None,
        request=_track_pages([_page(['a'])], calls, snapshot_id='snap-1'),
    )

    assert result['first_run'] is True
    assert store.track_ids('pl') == ['a']
    assert store.snapshot_id('pl') == 'snap-1'
    assert [c for c in calls if c['url'].endswith('/tracks')]


def test_no_metadata_falls_back_to_reading_the_tracks(tmp_path: Path):
    """The check is an optimisation: never a new way to miss a change."""

    store = SyncSnapshotStore(tmp_path / 'sync.json')
    store.save('pl', ['a'], snapshot_id='snap-1')
    calls = []
    result = spotify_sync.sync_playlist(
        _playlist(),
        config=_config(),
        store=store,
        apply=lambda n, a, r: None,
        request=_track_pages([_page(['a', 'b'])], calls, snapshot_id=''),
    )

    assert not result['skipped']
    assert result['added'] == ['b']


def _playlist(sid='pl', name='Mix'):
    return {'spotify_id': sid, 'name': name}


def test_sync_playlist_first_run_is_a_baseline(tmp_path: Path):
    store = SyncSnapshotStore(tmp_path / 'sync.json')
    calls = []
    applied = []

    def apply(name, added, removed):
        applied.append((name, added, removed))

    result = spotify_sync.sync_playlist(
        _playlist(),
        config=_config(),
        store=store,
        apply=apply,
        request=_track_pages([_page(['a', 'b'])], calls),
    )

    assert result['first_run'] is True
    assert result['changed'] is False
    assert applied == []
    assert store.track_ids('pl') == ['a', 'b']


def test_sync_playlist_applies_an_addition(tmp_path: Path):
    store = SyncSnapshotStore(tmp_path / 'sync.json')
    store.save('pl', ['a'])
    calls = []
    applied = []

    result = spotify_sync.sync_playlist(
        _playlist(),
        config=_config(),
        store=store,
        apply=lambda n, a, r: applied.append((n, a, r)),
        request=_track_pages([_page(['a', 'b'])], calls),
    )

    assert result['changed'] is True
    assert result['added'] == ['b']
    assert result['removed'] == []
    assert applied == [('Mix', ['b'], [])]
    assert store.track_ids('pl') == ['a', 'b']


def test_sync_playlist_applies_a_removal(tmp_path: Path):
    store = SyncSnapshotStore(tmp_path / 'sync.json')
    store.save('pl', ['a', 'b'])
    calls = []
    applied = []

    result = spotify_sync.sync_playlist(
        _playlist(),
        config=_config(),
        store=store,
        apply=lambda n, a, r: applied.append((n, a, r)),
        request=_track_pages([_page(['a'])], calls),
    )

    assert result['removed'] == ['b']
    assert result['added'] == []
    assert applied == [('Mix', [], ['b'])]
    assert store.track_ids('pl') == ['a']


def test_sync_playlist_no_change_never_calls_apply(tmp_path: Path):
    store = SyncSnapshotStore(tmp_path / 'sync.json')
    store.save('pl', ['a', 'b'])
    calls = []
    applied = []

    result = spotify_sync.sync_playlist(
        _playlist(),
        config=_config(),
        store=store,
        apply=lambda n, a, r: applied.append((n, a, r)),
        request=_track_pages([_page(['b', 'a'])], calls),
    )

    assert result['changed'] is False
    assert applied == []


def test_sync_playlist_reports_a_token_failure(tmp_path: Path):
    store = SyncSnapshotStore(tmp_path / 'sync.json')
    calls = []
    result = spotify_sync.sync_playlist(
        _playlist(),
        config=_config(token_expires_at=0, refresh_token=''),
        store=store,
        apply=lambda n, a, r: None,
        request=_track_pages([], calls),
    )
    assert result['error'] == 'auth_failed'
    assert store.track_ids('pl') is None


def test_sync_playlist_reports_an_apply_failure(tmp_path: Path):
    store = SyncSnapshotStore(tmp_path / 'sync.json')
    store.save('pl', ['a'])
    calls = []

    def boom(name, added, removed):
        raise RuntimeError('nope')

    result = spotify_sync.sync_playlist(
        _playlist(),
        config=_config(),
        store=store,
        apply=boom,
        request=_track_pages([_page(['a', 'b'])], calls),
    )
    assert result['error'] == 'apply_failed'
    # The baseline is not moved on, so the same diff is retried next time.
    assert store.track_ids('pl') == ['a']


def _refusing(calls, retry_after='15423'):
    """A request fake whose playlist fetch is always a 429."""

    def request(  # noqa: PLR0913, PLR0917
        method, url, *, headers=None, params=None, json=None, data=None
    ):
        calls.append(url)
        if 'api/token' in url:
            return FakeResponse(
                {'access_token': 'at', 'expires_in': 3600}, 200
            )
        return FakeResponse({}, 429, {'retry-after': retry_after})

    return request


def test_sync_playlist_reports_a_rate_limit_with_its_retry_after(
    tmp_path: Path,
):
    store = SyncSnapshotStore(tmp_path / 'sync.json')
    calls = []
    result = spotify_sync.sync_playlist(
        _playlist(),
        config=_config(),
        store=store,
        apply=lambda n, a, r: None,
        request=_refusing(calls),
    )
    assert result['error'] == 'rate_limited'
    assert result['retry_after'] == 15423
    # No baseline: nothing to diff against until Spotify answers again.
    assert store.track_ids('pl') is None


def test_run_sync_stops_asking_while_spotify_says_wait(tmp_path: Path):
    """The loop that fed the penalty: without a cooldown it asked every sweep."""

    store = SyncSnapshotStore(tmp_path / 'sync.json')
    first = []
    run_sync(
        [_playlist()],
        settings=_enabled_settings(),
        store=store,
        apply=lambda n, a, r: None,
        credentials=_config(),
        request=_refusing(first),
    )
    second = []
    summary = run_sync(
        [_playlist()],
        settings=_enabled_settings(),
        store=store,
        apply=lambda n, a, r: None,
        credentials=_config(),
        request=_refusing(second),
    )
    assert summary['rate_limited'] == 1
    assert summary['skipped'] == 1
    assert summary['retry_after_minutes'] > 0
    # Only the token POST - the playlist fetch was not repeated.
    assert not [url for url in second if '/tracks' in url]


def test_run_sync_force_asks_again_despite_the_cooldown(tmp_path: Path):
    store = SyncSnapshotStore(tmp_path / 'sync.json')
    calls = []
    run_sync(
        [_playlist()],
        settings=_enabled_settings(),
        store=store,
        apply=lambda n, a, r: None,
        credentials=_config(),
        request=_refusing(calls),
    )
    forced = []
    summary = run_sync(
        [_playlist()],
        settings=_enabled_settings(),
        store=store,
        apply=lambda n, a, r: None,
        credentials=_config(),
        request=_refusing(forced),
        force=True,
    )
    assert [url for url in forced if '/tracks' in url]
    assert summary['rate_limited'] == 1


# ── run_sync ─────────────────────────────────────────────────────────


def _enabled_settings(interval=60):
    return {'spotify_sync': {'enabled': True, 'interval_minutes': interval}}


def test_run_sync_does_nothing_when_disabled(tmp_path: Path):
    store = SyncSnapshotStore(tmp_path / 'sync.json')
    calls = []
    summary = run_sync(
        [_playlist()],
        settings={'spotify_sync': {'enabled': False}},
        store=store,
        apply=lambda n, a, r: None,
        credentials=_config(),
        request=_track_pages([_page(['a'])], calls),
    )
    assert summary['enabled'] is False
    assert summary['playlists'] == []
    # Nothing reached Spotify.
    assert calls == []


def test_run_sync_reports_not_connected(tmp_path: Path):
    store = SyncSnapshotStore(tmp_path / 'sync.json')
    summary = run_sync(
        [_playlist()],
        settings=_enabled_settings(),
        store=store,
        apply=lambda n, a, r: None,
        credentials=None,
    )
    assert summary['error'] == 'not_connected'
    assert summary['errors'] == 1


def test_run_sync_skips_a_playlist_that_is_not_due(tmp_path: Path):
    store = SyncSnapshotStore(tmp_path / 'sync.json')
    store.save('pl', ['a'])
    calls = []
    summary = run_sync(
        [_playlist()],
        settings=_enabled_settings(interval=60),
        store=store,
        apply=lambda n, a, r: None,
        credentials=_config(),
        request=_track_pages([_page(['a'])], calls),
    )
    assert summary['skipped'] == 1
    assert summary['playlists'] == []
    assert calls == []


def test_run_sync_force_ignores_disabled_and_interval(tmp_path: Path):
    store = SyncSnapshotStore(tmp_path / 'sync.json')
    store.save('pl', ['a'])
    calls = []
    summary = run_sync(
        [_playlist()],
        settings={'spotify_sync': {'enabled': False}},
        store=store,
        apply=lambda n, a, r: None,
        credentials=_config(),
        request=_track_pages([_page(['a', 'b'])], calls),
        force=True,
    )
    assert summary['enabled'] is False
    assert summary['added'] == 1
    assert summary['changed'] == 1


def test_run_sync_reports_renewed_tokens(tmp_path: Path):
    store = SyncSnapshotStore(tmp_path / 'sync.json')
    calls = []
    summary = run_sync(
        [_playlist()],
        settings=_enabled_settings(),
        store=store,
        apply=lambda n, a, r: None,
        credentials=_config(token_expires_at=0),
        request=_track_pages([_page(['a'])], calls),
    )
    assert summary['tokens']['access_token'] == 'at-new'


# ── apply_removals ───────────────────────────────────────────────────


class _Catalog:
    def __init__(self, rows) -> None:
        self.rows = list(rows)

    def list_tracks(self, _name):
        return list(self.rows)

    def remove_track(self, _name, tid):
        before = len(self.rows)
        self.rows = [r for r in self.rows if r['track_spotify_id'] != tid]
        return len(self.rows) != before


def test_apply_removals_drops_catalog_rows_and_m3u_lines(tmp_path: Path):
    downloads = tmp_path / 'downloads'
    (downloads / 'Artist').mkdir(parents=True)
    (downloads / 'Artist' / 'a.mp3').write_bytes(b'x')
    (downloads / 'Artist' / 'b.mp3').write_bytes(b'x')
    playlists = downloads / 'Playlists'
    playlists.mkdir(parents=True)
    m3u_path = playlists / 'Mix.m3u'
    m3u_path.write_text(
        '#EXTM3U\n'
        '#EXTINF:100,A - Alpha\n'
        '../Artist/a.mp3\n'
        '#EXTINF:100,B - Bravo\n'
        '../Artist/b.mp3\n',
        encoding='utf-8',
    )
    catalog = _Catalog([
        {'track_spotify_id': 'a', 'filename': 'Artist/a.mp3'},
        {'track_spotify_id': 'b', 'filename': 'Artist/b.mp3'},
    ])

    dropped = apply_removals(catalog, downloads, 'Mix', ['b'])

    assert dropped == 1
    assert [r['track_spotify_id'] for r in catalog.rows] == ['a']
    text = m3u_path.read_text(encoding='utf-8')
    assert '../Artist/a.mp3' in text
    assert 'A - Alpha' in text
    assert 'b.mp3' not in text
    assert 'Bravo' not in text


def test_apply_removals_noop_for_unknown_track(tmp_path: Path):
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    catalog = _Catalog([])
    assert apply_removals(catalog, downloads, 'Mix', ['zzz']) == 0


# ── settings plumbing (api) ──────────────────────────────────────────


def test_settings_default_is_off():
    block = api.DEFAULT_SETTINGS['spotify_sync']
    assert block['enabled'] is False
    assert block['interval_minutes'] == DEFAULT_INTERVAL_MINUTES


def test_spotify_sync_is_a_nested_setting():
    assert 'spotify_sync' in api._NESTED_SETTINGS


def test_clean_coerces_and_clamps():
    assert api._clean_spotify_sync({
        'enabled': 1,
        'interval_minutes': 3,
    }) == {'enabled': True, 'interval_minutes': MIN_INTERVAL_MINUTES}


def test_validate_rejects_enabled_without_a_connection():
    with pytest.raises(HTTPException):
        api._validate_spotify_sync_settings(
            {'enabled': True}, mirror={'client_id': ''}
        )


def test_validate_allows_enabled_with_a_client_id():
    api._validate_spotify_sync_settings(
        {'enabled': True}, mirror={'client_id': 'c'}
    )


def test_validate_skips_when_disabled():
    api._validate_spotify_sync_settings(
        {'enabled': False}, mirror={'client_id': ''}
    )


def test_sync_loop_idles_when_disabled(tmp_path: Path):
    """The loop returns promptly and never fetches while off."""

    calls = []
    store = SyncSnapshotStore(tmp_path / 'sync.json')

    async def run():
        task = asyncio.create_task(
            spotify_sync.spotify_sync_loop(
                get_settings=lambda: {'spotify_sync': {'enabled': False}},
                get_playlists=lambda: [_playlist()],
                get_credentials=_config,
                get_store=lambda: store,
                apply=lambda n, a, r: None,
                idle_seconds=0,
            )
        )
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(run())
    assert calls == []
