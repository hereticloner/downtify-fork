"""Stats endpoint (TDD, offline): library + download + playback numbers.

Aggregates from existing stores only: track index (library size),
playlist batch store (batches), activity log (downloads & playback),
likes, and the plays the Spotify history import mirrored. No new tables.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from starlette.testclient import TestClient

import main
from downtify import api, spotify_history
from downtify import stats as stats_mod


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
    app = TestClient(main.build_app(), base_url='http://testserver')
    app.post(
        '/api/auth/login', json={'username': 'admin', 'password': 'downtify'}
    )
    app.downloads = downloads
    return app


def test_stats_counts_downtify_play_in_canonical_history(client):
    response = client.post(
        '/api/activity/playback',
        json={
            'player': 'web',
            'state': 'playing',
            'track': {
                'file': 'A - T.mp3',
                'title': 'T',
                'artist': 'A',
                'duration': 100,
            },
            'position': 0,
        },
    )
    assert response.status_code == 200, response.text
    data = client.get('/api/stats').json()['playback']
    assert data['total'] == 1
    assert data['recent'][0]['source'] == 'downtify'
    assert data['measured']['plays'] == 1
    assert data['measured']['seconds'] == 0


def test_stats_counts_spotify_and_lastfm_without_faking_measured_time(client):
    listening = api.state.listening
    listening.link_or_create(
        user_id=1,
        source='spotify',
        source_key='s1',
        played_at='2026-11-25T20:15:00Z',
        artist='A',
        title='T',
    )
    listening.link_or_create(
        user_id=1,
        source='lastfm',
        source_key='l1',
        played_at='2026-11-25T21:15:00Z',
        artist='B',
        title='U',
    )
    data = client.get('/api/stats').json()['playback']
    assert data['total'] == 2
    assert {row['source'] for row in data['recent']} == {'spotify', 'lastfm'}
    assert data['measured']['seconds'] == 0
    assert data['measured']['plays'] == 0


def test_stats_period_aggregates_follow_selected_window(client):
    listening = api.state.listening
    today = datetime.now(timezone.utc).date()
    for source, key, offset in (
        ('spotify', 's7', 0),
        ('lastfm', 'l30', 8),
        ('downtify', 'd90', 40),
    ):
        listening.link_or_create(
            user_id=1,
            source=source,
            source_key=key,
            played_at=f'{(today - timedelta(days=offset)).isoformat()}T20:15:00Z',
            artist=source,
            title=key,
        )

    seven = client.get('/api/stats', params={'days': 7}).json()['playback']
    thirty = client.get('/api/stats', params={'days': 30}).json()['playback']
    ninety = client.get('/api/stats', params={'days': 90}).json()['playback']

    assert [
        seven['period']['total'],
        thirty['period']['total'],
        ninety['period']['total'],
    ] == [1, 2, 3]
    assert seven['total'] == thirty['total'] == ninety['total'] == 3
    assert ninety['period']['by_source'] == {
        'downtify': 1,
        'spotify': 1,
        'lastfm': 1,
    }


def test_best_day_is_the_older_maximum_not_the_newest_active_day(client):
    listening = api.state.listening
    today = datetime.now(timezone.utc).date()
    older = today - timedelta(days=10)
    for index in range(40):
        listening.link_or_create(
            user_id=1,
            source='spotify',
            source_key=f'older:{index}',
            played_at=f'{older.isoformat()}T20:15:00Z',
            artist='A',
            title=f'T{index}',
        )
    listening.link_or_create(
        user_id=1,
        source='lastfm',
        source_key='newest',
        played_at=f'{today.isoformat()}T20:15:00Z',
        artist='B',
        title='Newest',
    )

    assert client.get('/api/stats').json()['playback']['best_day'] == {
        'date': older.isoformat(),
        'count': 40,
    }


def test_downtify_spotify_lastfm_same_play_is_one_event(client):
    listening = api.state.listening
    listening.link_or_create(
        user_id=1,
        source='downtify',
        source_key='activity:1',
        played_at='2026-11-25T20:15:00Z',
        artist='A',
        title='T',
        spotify_track_id='s1',
    )
    listening.link_or_create(
        user_id=1,
        source='spotify',
        source_key='spotify:1',
        played_at='2026-11-25T20:15:01Z',
        artist='A',
        title='T',
        spotify_track_id='s1',
    )
    listening.link_or_create(
        user_id=1,
        source='lastfm',
        source_key='lastfm:1',
        played_at='2026-11-25T20:18:00Z',
        artist='A',
        title='T',
    )
    data = client.get('/api/stats').json()['playback']
    assert data['total'] == 1
    assert data['recent'][0]['source'] == 'downtify'


def test_canonical_history_is_user_scoped_and_server_total_is_admin_only(
    client,
):
    second = api.state.auth.users.create('second', 'second-password')
    _device, token = api.state.auth.create_device(
        'second phone', user_id=second['id']
    )
    api.state.listening.link_or_create(
        user_id=1,
        source='spotify',
        source_key='s1',
        played_at='2026-11-25T20:15:00Z',
        artist='A',
        title='T',
    )
    api.state.listening.link_or_create(
        user_id=second['id'],
        source='lastfm',
        source_key='l1',
        played_at='2026-11-25T21:15:00Z',
        artist='B',
        title='U',
    )
    assert client.get('/api/stats').json()['playback']['total'] == 1
    assert (
        client.get('/api/stats', params={'scope': 'server'}).json()[
            'playback'
        ]['total']
        == 2
    )
    forbidden = client.get(
        '/api/stats',
        params={'scope': 'server'},
        headers={'Authorization': f'Bearer {token}'},
    )
    assert forbidden.status_code == 403


def test_priority_upgrade_moves_heatmap_to_the_correct_day(client):
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    listening = api.state.listening
    listening.link_or_create(
        user_id=1,
        source='lastfm',
        source_key='l1',
        played_at=f'{today.isoformat()}T00:00:30Z',
        artist='A',
        title='T',
    )
    listening.link_or_create(
        user_id=1,
        source='downtify',
        source_key='activity:1',
        played_at=f'{yesterday.isoformat()}T23:58:00Z',
        artist='A',
        title='T',
    )
    counts = {
        row['date']: row['count']
        for row in client.get('/api/stats').json()['playback']['heatmap']
    }
    assert counts[today.isoformat()] == 0
    assert counts[yesterday.isoformat()] == 1


def test_stats_measured_metrics_are_user_scoped(client):
    first = api.state.auth.users.create('first', 'first-password')
    second = api.state.auth.users.create('second', 'second-password')
    _first_device, first_token = api.state.auth.create_device(
        'first phone', user_id=first['id']
    )
    _second_device, second_token = api.state.auth.create_device(
        'second phone', user_id=second['id']
    )
    for headers, username, count in (
        ({'Authorization': f'Bearer {first_token}'}, 'first', 1),
        ({'Authorization': f'Bearer {second_token}'}, 'second', 2),
    ):
        for index in range(count):
            response = client.post(
                '/api/activity/playback',
                json={
                    'player': 'app',
                    'state': 'playing',
                    'track': {
                        'file': f'A - {username}-{index}.mp3',
                        'duration': 100,
                    },
                    'position': 0,
                },
                headers=headers,
            )
            assert response.status_code == 200, response.text

    personal = client.get(
        '/api/stats', headers={'Authorization': f'Bearer {first_token}'}
    )
    assert personal.status_code == 200, personal.text
    assert personal.json()['playback']['measured']['plays'] == 1

    server = client.get('/api/stats', params={'scope': 'server'})
    assert server.status_code == 200, server.text
    assert server.json()['playback']['measured']['plays'] == 3

    forbidden = client.get(
        '/api/stats',
        params={'scope': 'server'},
        headers={'Authorization': f'Bearer {first_token}'},
    )
    assert forbidden.status_code == 403


def test_stats_endpoint_shape_with_empty_stores(client):
    resp = client.get('/api/stats')
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert set(data) >= {
        'library',
        'downloads',
        'playback',
        'spotify',
    }
    assert isinstance(data['library']['likes'], int)
    assert isinstance(data['library']['tracks'], int)
    assert isinstance(data['downloads']['total'], int)
    assert isinstance(data['downloads']['last_30_days'], int)
    assert isinstance(data['playback']['total'], int)
    assert isinstance(data['playback']['top_tracks'], list)
    assert isinstance(data['spotify']['recent'], list)
    assert isinstance(data['spotify']['play_count'], int)


def test_stats_counts_activity_kinds(client):
    """Downloads and playback are read from the activity log."""

    log = api.state.activity
    assert log is not None
    log.record('download', user_id=1, summary='Song A')
    log.record('download', user_id=1, summary='Song B')
    log.record('playback', user_id=1, summary='Song A')
    _sync_activity()
    resp = client.get('/api/stats')
    data = resp.json()
    assert data['downloads']['total'] >= 2
    assert data['playback']['total'] >= 1
    assert data['playback']['top_tracks'][0]['summary'] == 'Song A'


def test_stats_reports_mirrored_spotify_plays(client, monkeypatch):
    """The plays the history import stored ride along in `spotify`."""

    seen: dict[str, object] = {}

    def fake_recent(db_path, limit=50):
        seen['db_path'] = db_path
        seen['limit'] = limit
        return [
            {
                'played_at': '2026-10-12T21:15:00+00:00',
                'artist_name': 'The Night Owls',
                'track_name': 'Do I Still Recall',
                'album_name': 'Night Owls',
                'spotify_track_id': 'abc',
                'duration_ms': 201000,
                'synced_at': '2026-10-13T00:00:00+00:00',
            },
            {
                'played_at': '2026-10-12T20:58:00+00:00',
                'artist_name': 'Blue Static',
                'track_name': 'Long Way Down',
            },
        ]

    monkeypatch.setattr(
        spotify_history, 'get_recent_from_spotify', fake_recent
    )
    monkeypatch.setattr(spotify_history, 'count_plays', lambda db_path: 12)

    data = client.get('/api/stats').json()

    assert Path(seen['db_path']).name == 'downtify_activity.db'
    assert data['spotify']['play_count'] == 12
    assert data['spotify']['recent'][0] == {
        'played_at': '2026-10-12T21:15:00+00:00',
        'artist_name': 'The Night Owls',
        'track_name': 'Do I Still Recall',
        'album_name': 'Night Owls',
    }
    assert data['spotify']['recent'][1]['track_name'] == 'Long Way Down'


def test_stats_caps_the_spotify_panel_at_ten(client, monkeypatch):
    """The store keeps a page of fifty; the response lists ten."""

    rows = [
        {
            'played_at': f'2026-10-12T21:{minute:02d}:00+00:00',
            'artist_name': 'Blue Static',
            'track_name': f'Song {minute}',
        }
        for minute in range(12)
    ]
    monkeypatch.setattr(
        spotify_history, 'get_recent_from_spotify', lambda db, limit=50: rows
    )
    data = client.get('/api/stats').json()
    recent = data['spotify']['recent']
    assert len(recent) == 10
    assert recent[0] == {**rows[0], 'album_name': ''}
    assert recent[-1]['track_name'] == 'Song 9'
    # Never fewer than the list itself shows.
    assert data['spotify']['play_count'] == 10


def test_stats_spotify_survives_a_broken_history_store(client, monkeypatch):
    """A history store that cannot be read is an empty panel, not a 500."""

    def boom(*args, **kwargs):
        raise sqlite3.OperationalError('no such table')

    monkeypatch.setattr(spotify_history, 'get_recent_from_spotify', boom)
    resp = client.get('/api/stats')
    assert resp.status_code == 200, resp.text
    assert resp.json()['spotify'] == {'recent': [], 'play_count': 0}


# ── the listening heatmap ──────────────────────────────────────────────────


def _sync_activity() -> None:
    api.state.listening.backfill_activity(api.state.activity)


def _record_on(kind: str, day: date, summary: str = 'Song') -> None:
    """An activity entry stamped on *day* rather than on now."""

    with sqlite3.connect(main.DATABASE_DIR / 'downtify_activity.db') as conn:
        conn.execute(
            'INSERT INTO activity (at, user_id, username, kind, summary, '
            'detail_json, client, ip) '
            "VALUES (?, 1, 'admin', ?, ?, '{}', 'test', '')",
            (f'{day.isoformat()}T20:00:00+00:00', kind, summary),
        )


def test_stats_ships_a_dense_year_of_heatmap_days(client):
    """Every day of the retained window, so the grid has no holes."""

    data = client.get('/api/stats').json()
    heatmap = data['playback']['heatmap']
    assert len(heatmap) == stats_mod.HEATMAP_WEEKS * 7

    today = datetime.now(timezone.utc).date()
    # Oldest first, ending today.
    assert heatmap[-1]['date'] == today.isoformat()
    assert (
        heatmap[0]['date']
        == (today - timedelta(days=len(heatmap) - 1)).isoformat()
    )
    assert all(set(day) == {'date', 'count'} for day in heatmap)
    assert all(isinstance(day['count'], int) for day in heatmap)

    # Nothing played yet: no streak, and no busiest day to name.
    assert data['playback']['streak_days'] == 0
    assert data['playback']['best_day'] == {'date': '', 'count': 0}


def test_stats_heatmap_counts_the_plays_of_each_day(client):
    """Counts plays per day - downloads don't colour the grid."""

    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    before_that = today - timedelta(days=2)
    for _ in range(3):
        _record_on('playback', yesterday)
    _record_on('playback', before_that)
    _record_on('download', today)

    _sync_activity()
    data = client.get('/api/stats').json()
    counts = {d['date']: d['count'] for d in data['playback']['heatmap']}
    assert counts[yesterday.isoformat()] == 3
    assert counts[before_that.isoformat()] == 1
    assert counts[today.isoformat()] == 0
    assert data['playback']['best_day'] == {
        'date': yesterday.isoformat(),
        'count': 3,
    }
    # A today still to come doesn't break the run: yesterday and the
    # day before it are two days in a row.
    assert data['playback']['streak_days'] == 2


def test_stats_streak_counts_today_when_there_were_plays(client):
    today = datetime.now(timezone.utc).date()
    for offset in range(4):
        _record_on('playback', today - timedelta(days=offset))

    _sync_activity()
    data = client.get('/api/stats').json()
    assert data['playback']['streak_days'] == 4


# ── where a play came from ──────────────────────────────────────────────────


def _play_from(day: date, summary: str, context: str, kind: str = 'playlist'):
    """A playback entry whose queue came from a named playlist."""

    with sqlite3.connect(main.DATABASE_DIR / 'downtify_activity.db') as conn:
        conn.execute(
            'INSERT INTO activity (at, user_id, username, kind, summary, '
            "detail_json, client, ip) VALUES (?, 1, 'admin', "
            "'playback', ?, ?, 'test', '')",
            (
                f'{day.isoformat()}T20:00:00+00:00',
                summary,
                json.dumps({
                    'track': {
                        'title': summary,
                        'context': context,
                        'context_type': kind,
                    }
                }),
            ),
        )


def test_stats_reports_the_queue_a_play_came_from(client):
    """The recent panel says which playlist the play was served from."""

    today = datetime.now(timezone.utc).date()
    _play_from(today, 'Roads', 'Chill Deploy')
    _play_from(today, 'Dummy', 'Chill Deploy')
    _play_from(today, 'Roads', 'Gece')

    _sync_activity()
    recent = client.get('/api/stats').json()['playback']['recent']
    assert len(recent) == 3
    assert {r['context'] for r in recent} == {'Chill Deploy', 'Gece'}
    assert all(r['date'] == today.isoformat() for r in recent)
    assert all(r['at'].startswith(today.isoformat()) for r in recent)
    assert {r['summary'] for r in recent} == {'Roads', 'Dummy'}


def test_stats_counts_the_queues_played_most(client):
    """The same plays, grouped by the queue that served them."""

    today = datetime.now(timezone.utc).date()
    _play_from(today, 'A', 'Chill Deploy')
    _play_from(today, 'B', 'Chill Deploy')
    _play_from(today, 'C', 'Gece')
    # A play with no queue at all (a bare library play) isn't a queue.
    with sqlite3.connect(main.DATABASE_DIR / 'downtify_activity.db') as conn:
        conn.execute(
            'INSERT INTO activity (at, user_id, username, kind, summary, '
            "detail_json, client, ip) VALUES (?, 1, 'admin', 'playback', "
            "'D', ?, 'test', '')",
            (f'{today.isoformat()}T20:00:00+00:00', '{}'),
        )

    _sync_activity()
    contexts = client.get('/api/stats').json()['playback']['top_contexts']
    assert contexts[0] == {'context': 'Chill Deploy', 'count': 2}
    assert contexts[1] == {'context': 'Gece', 'count': 1}


def test_stats_recent_plays_are_capped(client):
    """The panel lists a page of plays, not the whole retained year."""

    today = datetime.now(timezone.utc).date()
    for n in range(stats_mod.PLAYBACK_RECENT_LIMIT + 10):
        _play_from(today, f'Song {n}', 'Chill Deploy')

    _sync_activity()
    recent = client.get('/api/stats').json()['playback']['recent']
    assert len(recent) == stats_mod.PLAYBACK_RECENT_LIMIT


def test_stats_survives_a_playback_entry_without_detail(client):
    """An entry the log wrote with no detail is still a play, not a 500."""

    with sqlite3.connect(main.DATABASE_DIR / 'downtify_activity.db') as conn:
        conn.execute(
            'INSERT INTO activity (at, user_id, username, kind, summary, '
            "detail_json, client, ip) VALUES ('2026-10-12T20:00:00+00:00', "
            "1, 'admin', 'playback', 'Song A', 'not json', 'test', '')"
        )

    _sync_activity()
    resp = client.get('/api/stats')
    assert resp.status_code == 200, resp.text
    recent = resp.json()['playback']['recent']
    assert recent[0]['summary'] == 'Song A'
    assert not recent[0]['context']


# ── the two builders, on a fixed clock ─────────────────────────────────────


def test_heatmap_counts_one_entry_per_day_oldest_first():
    entries = [
        {'at': '2026-10-11T08:00:00+00:00'},
        {'at': '2026-10-11T21:00:00+00:00'},
        {'at': '2026-10-09T08:00:00+00:00'},
    ]
    days = stats_mod.build_activity_heatmap(
        entries, weeks=2, today=date(2026, 10, 12)
    )
    assert len(days) == 14
    assert days[0]['date'] == '2026-09-29'
    assert days[-1] == {'date': '2026-10-12', 'count': 0}
    assert days[-2] == {'date': '2026-10-11', 'count': 2}
    assert days[-4] == {'date': '2026-10-09', 'count': 1}


def test_heatmap_never_promises_more_days_than_the_log_keeps():
    """A wider ask than the activity log retains is capped at retention."""

    days = stats_mod.build_activity_heatmap(
        [], weeks=500, today=date(2026, 10, 12)
    )
    assert stats_mod.HEATMAP_WEEKS == 52
    assert len(days) == 52 * 7


def test_streak_counts_back_from_today_but_stops_at_a_gap():
    today = date(2026, 10, 12)
    played = [
        {'at': f'{(today - timedelta(days=n)).isoformat()}T20:00:00+00:00'}
        for n in range(3)
    ]
    assert stats_mod.build_listening_streak(played, today=today) == 3
    # Yesterday and the day before it are still consecutive.
    assert stats_mod.build_listening_streak(played[1:], today=today) == 2
    # Nothing for two days is a finished streak, not one about to start.
    assert stats_mod.build_listening_streak([], today=today) == 0
