import asyncio
import json
import sqlite3

import pytest

from downtify import lastfm_history
from downtify.listening_history import ListeningStore


class FakeResponse:
    def __init__(self, body, status_code=200):
        self._body = body
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f'HTTP {self.status_code}')

    def json(self):
        return self._body


def test_fetch_uses_public_read_params_and_skips_nowplaying():
    calls = []

    def sender(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return FakeResponse({
            'recenttracks': {
                'track': [
                    {
                        'name': 'T',
                        'artist': {'name': 'A'},
                        'date': {'uts': '1'},
                        'nowplaying': 'true',
                    },
                    {
                        'name': 'U',
                        'artist': {'name': 'B'},
                        'date': {'uts': '2'},
                    },
                ]
            }
        })

    body = lastfm_history.fetch_recent_tracks(
        {'api_key': 'k', 'username': 'u'},
        from_uts=10,
        to_uts=20,
        limit=200,
        request=sender,
    )
    params = calls[0][2]['params']
    assert params == {
        'method': 'user.getRecentTracks',
        'user': 'u',
        'api_key': 'k',
        'format': 'json',
        'limit': 200,
        'from': 10,
        'to': 20,
        'extended': 1,
    }
    assert [row['track_name'] for row in lastfm_history.parse_plays(body)] == [
        'U'
    ]


def test_raw_rows_occurrences_and_links_are_idempotent(tmp_path):
    db = tmp_path / 'activity.db'
    raw = {'name': 'T', 'artist': {'name': 'A'}, 'date': {'uts': '100'}}
    rows = [
        {
            'played_at': '1970-01-01T00:01:40+00:00',
            'uts': 100,
            'artist_name': 'A',
            'track_name': 'T',
            'album_name': '',
            'mbid': '',
            'raw_item': raw,
        },
        {
            'played_at': '1970-01-01T00:01:40+00:00',
            'uts': 100,
            'artist_name': 'A',
            'track_name': 'T',
            'album_name': '',
            'mbid': '',
            'raw_item': raw,
        },
    ]
    assert lastfm_history.save_recent_tracks(db, rows, user_id=1) == 2
    assert lastfm_history.save_recent_tracks(db, rows, user_id=1) == 0
    assert lastfm_history.count_plays(db) == 2
    listening = ListeningStore(db)
    assert lastfm_history.link_pending(db, listening, user_id=1) == 2
    assert lastfm_history.link_pending(db, listening, user_id=1) == 0
    assert listening.stats(user_id=1)['total'] == 2

    with sqlite3.connect(db) as conn:
        stored = conn.execute(
            'SELECT source_key, raw_json FROM lastfm_recent_tracks ORDER BY id'
        ).fetchall()
    assert stored[0][0] != stored[1][0]
    assert json.loads(stored[0][1]) == raw


def test_backfill_resumes_from_oldest_and_catches_up_newest(tmp_path):
    newest_page = {
        'recenttracks': {
            '@attr': {'totalPages': '2'},
            'track': [
                {
                    'name': 'New',
                    'artist': {'name': 'A'},
                    'date': {'uts': '200'},
                },
                {
                    'name': 'Old',
                    'artist': {'name': 'A'},
                    'date': {'uts': '100'},
                },
            ],
        }
    }
    older_page = {
        'recenttracks': {
            'track': [
                {
                    'name': 'Older',
                    'artist': {'name': 'A'},
                    'date': {'uts': '50'},
                },
            ]
        }
    }

    def sender(method, url, **kwargs):
        params = kwargs['params']
        if params.get('from') is not None:
            return FakeResponse({'recenttracks': {'track': []}})
        if params.get('to') is not None:
            return FakeResponse(older_page)
        return FakeResponse(newest_page)

    settings = {
        'scrobbling': {
            'enabled': True,
            'lastfm_enabled': True,
            'lastfm_api_key': 'k',
            'lastfm_username': 'u',
            'import_history': True,
        }
    }
    db = tmp_path / 'activity.db'
    first = lastfm_history.run_once(settings, db, max_pages=1, request=sender)
    second = lastfm_history.run_once(settings, db, max_pages=1, request=sender)
    assert first['saved'] == 2
    assert second['saved'] == 1
    assert lastfm_history.count_plays(db) == 3


def test_lastfm_error_body_does_not_advance_cursor(tmp_path):
    settings = {
        'scrobbling': {
            'enabled': True,
            'lastfm_enabled': True,
            'lastfm_api_key': 'k',
            'lastfm_username': 'u',
            'import_history': True,
        }
    }

    def sender(method, url, **kwargs):
        return FakeResponse({
            'lfm': {'status': 'failed', 'error': {'code': '16'}}
        })

    db = tmp_path / 'activity.db'
    summary = lastfm_history.run_once(settings, db, request=sender)
    assert summary['error'] == 'fetch_failed'
    assert lastfm_history.count_plays(db) == 0
    assert lastfm_history._load_state(db) == {
        'newest_at': '',
        'oldest_at': '',
        'backfill_done': False,
    }


def test_save_ignores_malformed_timestamp_rows(tmp_path):
    db = tmp_path / 'activity.db'
    rows = [
        {
            'uts': 'junk',
            'played_at': 'bad',
            'artist_name': 'A',
            'track_name': 'T',
        },
        'junk',
        {
            'uts': 100,
            'played_at': '1970-01-01T00:01:40+00:00',
            'artist_name': 'A',
            'track_name': 'T',
        },
    ]
    assert lastfm_history.save_recent_tracks(db, rows) == 1
    assert lastfm_history.count_plays(db) == 1


@pytest.mark.asyncio
async def test_loop_imports_and_links_one_page(tmp_path, monkeypatch):
    db = tmp_path / 'activity.db'
    listening = ListeningStore(db)
    settings = {
        'scrobbling': {
            'enabled': True,
            'lastfm_enabled': True,
            'lastfm_api_key': 'k',
            'lastfm_username': 'u',
            'import_history': True,
        }
    }

    def sender(method, url, **kwargs):
        return FakeResponse({
            'recenttracks': {
                'track': [
                    {
                        'name': 'T',
                        'artist': {'name': 'A'},
                        'date': {'uts': '100'},
                    }
                ]
            }
        })

    async def stop(_delay):
        raise asyncio.CancelledError

    monkeypatch.setattr(lastfm_history.asyncio, 'sleep', stop)
    with pytest.raises(asyncio.CancelledError):
        await lastfm_history.lastfm_history_loop(
            lambda: settings,
            db,
            listening_getter=lambda: listening,
            user_id_getter=lambda: 1,
            request=sender,
        )
    assert lastfm_history.count_plays(db) == 1
    assert listening.stats(user_id=1)['total'] == 1


def test_import_switch_and_read_config_require_public_credentials():
    settings = {
        'scrobbling': {
            'enabled': True,
            'lastfm_enabled': True,
            'lastfm_api_key': 'k',
            'lastfm_username': 'u',
            'import_history': True,
        }
    }
    assert lastfm_history.import_enabled(settings) is True
    assert lastfm_history.read_config(settings) == {
        'api_key': 'k',
        'username': 'u',
    }
    settings['scrobbling']['import_history'] = False
    assert lastfm_history.import_enabled(settings) is False
    assert lastfm_history.read_config(settings) is None


def test_http_429_does_not_advance_cursor(tmp_path):
    settings = {
        'scrobbling': {
            'enabled': True,
            'lastfm_enabled': True,
            'lastfm_api_key': 'k',
            'lastfm_username': 'u',
            'import_history': True,
        }
    }

    def sender(method, url, **kwargs):
        return FakeResponse({}, status_code=429)

    db = tmp_path / 'activity.db'
    summary = lastfm_history.run_once(settings, db, request=sender)
    assert summary['error'] == 'fetch_failed'
    assert lastfm_history.count_plays(db) == 0
    assert not lastfm_history._load_state(db)['oldest_at']


def test_failed_page_write_does_not_advance_cursor(tmp_path):
    settings = {
        'scrobbling': {
            'enabled': True,
            'lastfm_enabled': True,
            'lastfm_api_key': 'k',
            'lastfm_username': 'u',
            'import_history': True,
        }
    }
    db = tmp_path / 'activity.db'
    lastfm_history.ensure_schema(db)
    with sqlite3.connect(db) as conn:
        conn.execute(
            'CREATE TRIGGER fail_lastfm_insert BEFORE INSERT ON '
            "lastfm_recent_tracks BEGIN SELECT RAISE(ABORT, 'disk full'); END"
        )

    def sender(method, url, **kwargs):
        return FakeResponse({
            'recenttracks': {
                'track': [
                    {
                        'name': 'T',
                        'artist': {'name': 'A'},
                        'date': {'uts': '100'},
                    }
                ]
            }
        })

    with pytest.raises(sqlite3.IntegrityError, match='disk full'):
        lastfm_history.run_once(settings, db, request=sender)
    assert lastfm_history.count_plays(db) == 0
    assert lastfm_history._load_state(db) == {
        'newest_at': '',
        'oldest_at': '',
        'backfill_done': False,
    }
