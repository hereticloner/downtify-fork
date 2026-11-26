import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from downtify.listening_history import ListeningStore, normalize_match_key


def test_same_source_is_idempotent(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    first, created = store.link_or_create(
        user_id=1,
        source='spotify',
        source_key='spotify:1',
        played_at='2026-11-25T20:15:00Z',
        artist='A',
        title='T',
    )
    again, created_again = store.link_or_create(
        user_id=1,
        source='spotify',
        source_key='spotify:1',
        played_at='2026-11-25T20:15:00Z',
        artist='A',
        title='T',
    )
    assert (first, created, again, created_again) == (1, True, 1, False)


def test_higher_priority_promotes_without_changing_identity(tmp_path):
    db = tmp_path / 'activity.db'
    store = ListeningStore(db)
    event_id, _ = store.link_or_create(
        user_id=1,
        source='lastfm',
        source_key='lastfm:1',
        played_at='2026-11-25T23:59:30Z',
        artist='A',
        title='T',
    )
    promoted, created = store.link_or_create(
        user_id=1,
        source='downtify',
        source_key='activity:9',
        played_at='2026-11-25T23:56:00Z',
        artist='A',
        title='T',
        spotify_track_id='spotify-1',
    )
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            'SELECT source, source_key, identity_key, played_at, '
            'spotify_track_id FROM listening_events WHERE id=?',
            (event_id,),
        ).fetchone()
    assert (promoted, created) == (event_id, False)
    assert row == (
        'downtify',
        'activity:9',
        'lastfm:lastfm:1',
        '2026-11-25T23:56:00Z',
        'spotify-1',
    )


def test_promoted_and_merged_observations_remain_idempotent(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    event_id, _ = store.link_or_create(
        user_id=1,
        source='lastfm',
        source_key='lastfm:1',
        played_at='2026-11-25T20:18:00Z',
        artist='A',
        title='T',
    )
    store.link_or_create(
        user_id=1,
        source='spotify',
        source_key='spotify:1',
        played_at='2026-11-25T20:15:01Z',
        artist='A',
        title='T',
    )
    store.link_or_create(
        user_id=1,
        source='downtify',
        source_key='activity:1',
        played_at='2026-11-25T20:15:00Z',
        artist='A',
        title='T',
    )
    for source, key, at in (
        ('lastfm', 'lastfm:1', '2026-11-25T20:18:00Z'),
        ('spotify', 'spotify:1', '2026-11-25T20:15:01Z'),
        ('downtify', 'activity:1', '2026-11-25T20:15:00Z'),
    ):
        again, created = store.link_or_create(
            user_id=1,
            source=source,
            source_key=key,
            played_at=at,
            artist='A',
            title='T',
        )
        assert (again, created) == (event_id, False)
    assert store.stats(user_id=1)['total'] == 1


def test_concurrent_sources_merge_one_play(tmp_path):
    for index in range(20):
        store = ListeningStore(tmp_path / f'activity-{index}.db')
        barrier = threading.Barrier(2)

        def add(source, key, at):
            barrier.wait()
            return store.link_or_create(
                user_id=1,
                source=source,
                source_key=key,
                played_at=at,
                artist='A',
                title='T',
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            downtify = pool.submit(
                add, 'downtify', 'activity:1', '2026-11-25T20:15:00Z'
            )
            spotify = pool.submit(
                add, 'spotify', 'spotify:1', '2026-11-25T20:15:01Z'
            )
            ids = {downtify.result()[0], spotify.result()[0]}
        assert len(ids) == 1
        assert store.stats(user_id=1)['total'] == 1


def test_same_source_second_observation_is_a_new_play(tmp_path):
    db = tmp_path / 'activity.db'
    store = ListeningStore(db)
    store.link_or_create(
        user_id=1,
        source='spotify',
        source_key='spotify:1',
        played_at='2026-11-25T20:15:00Z',
        artist='A',
        title='T',
    )
    second, created = store.link_or_create(
        user_id=1,
        source='spotify',
        source_key='spotify:2',
        played_at='2026-11-25T20:20:00Z',
        artist='A',
        title='T',
    )
    with sqlite3.connect(db) as conn:
        count = conn.execute(
            'SELECT COUNT(*) FROM listening_events'
        ).fetchone()[0]
    assert created is True
    assert second != 1
    assert count == 2


def test_stats_are_user_scoped_and_sql_aggregated(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    today = datetime.now(timezone.utc).date().isoformat()
    store.link_or_create(
        user_id=1,
        source='spotify',
        source_key='s1',
        played_at=f'{today}T20:15:00Z',
        artist='A',
        title='T',
        context='Mix',
        context_type='playlist',
    )
    store.link_or_create(
        user_id=2,
        source='lastfm',
        source_key='l1',
        played_at=f'{today}T21:15:00Z',
        artist='B',
        title='U',
    )
    personal = store.stats(user_id=1)
    assert personal['total'] == 1
    assert personal['top_tracks'] == [{'summary': 'A - T', 'count': 1}]
    assert personal['daily'] == [{'date': today, 'count': 1}]
    assert personal['top_contexts'] == [{'context': 'Mix', 'count': 1}]
    assert personal['recent'][0]['source'] == 'spotify'
    assert store.stats(user_id=0)['total'] == 2


def test_forget_user_removes_events_and_source_links(tmp_path):
    db = tmp_path / 'activity.db'
    store = ListeningStore(db)
    event_id, _ = store.link_or_create(
        user_id=1,
        source='spotify',
        source_key='s1',
        played_at='2026-11-25T20:15:00Z',
        artist='A',
        title='T',
    )
    store.link_or_create(
        user_id=2,
        source='lastfm',
        source_key='l1',
        played_at='2026-11-25T21:15:00Z',
        artist='B',
        title='U',
    )
    assert store.forget_user(1) == 2
    with sqlite3.connect(db) as conn:
        assert (
            conn.execute(
                'SELECT COUNT(*) FROM listening_events WHERE user_id=1'
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                'SELECT COUNT(*) FROM listening_event_sources WHERE event_id=?',
                (event_id,),
            ).fetchone()[0]
            == 0
        )
    assert store.stats(user_id=0)['total'] == 1


def test_match_key_normalizes_unicode_case_and_whitespace():
    assert normalize_match_key('  ÄRTIST\u00a0 ', ' TITLE  ') == 'ärtist|title'


def test_same_track_outside_match_window_is_a_new_play(tmp_path):
    db = tmp_path / 'activity.db'
    store = ListeningStore(db)
    store.link_or_create(
        user_id=1,
        source='spotify',
        source_key='s1',
        played_at='2026-11-25T20:15:00Z',
        artist='A',
        title='T',
    )
    second, created = store.link_or_create(
        user_id=1,
        source='lastfm',
        source_key='l1',
        played_at='2026-11-25T20:46:00Z',
        artist='A',
        title='T',
    )
    assert created is True
    assert second != 1


def test_period_aggregates_count_canonical_events_once(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    today = datetime.now(timezone.utc).date().isoformat()
    store.link_or_create(
        user_id=1,
        source='lastfm',
        source_key='lastfm:1',
        played_at=f'{today}T20:18:00Z',
        artist='A',
        title='T',
    )
    store.link_or_create(
        user_id=1,
        source='spotify',
        source_key='spotify:1',
        played_at=f'{today}T20:15:00Z',
        artist='A',
        title='T',
    )

    data = store.stats(user_id=1, days=7)

    assert data['period'] == {
        'days': 7,
        'total': 1,
        'by_source': {'downtify': 0, 'spotify': 1, 'lastfm': 0},
    }


def test_period_aggregates_report_unique_duration_and_utc_patterns(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    today = datetime.now(timezone.utc).date()
    store.link_or_create(
        user_id=1,
        source='spotify',
        source_key='spotify:1',
        played_at=f'{today.isoformat()}T01:15:00Z',
        artist='A',
        title='T',
        album='Album',
        duration_ms=5000,
    )
    store.link_or_create(
        user_id=1,
        source='lastfm',
        source_key='lastfm:1',
        played_at=f'{today.isoformat()}T02:30:00Z',
        artist='A',
        title='U',
    )
    store.link_or_create(
        user_id=1,
        source='downtify',
        source_key='activity:old',
        played_at=f'{(today - timedelta(days=8)).isoformat()}T03:30:00Z',
        artist='Old',
        title='Outside',
        duration_ms=9000,
    )

    data = store.stats(user_id=1, days=7)

    assert data['unique'] == {'tracks': 2, 'artists': 1, 'albums': 1}
    assert data['track_time'] == {
        'seconds': 5,
        'plays_with_duration': 1,
        'plays_without_duration': 1,
    }
    assert len(data['patterns']['by_hour']) == 24
    assert data['patterns']['by_hour'][1:3] == [1, 1]
    assert len(data['patterns']['by_weekday']) == 7
    assert sum(data['patterns']['by_hour']) == 2
    assert sum(data['patterns']['by_weekday']) == 2


def test_period_aggregates_are_user_scoped_and_exclude_future_plays(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    today = datetime.now(timezone.utc).date()
    store.link_or_create(
        user_id=1,
        source='spotify',
        source_key='s1',
        played_at=f'{today.isoformat()}T20:15:00Z',
        artist='A',
        title='T',
    )
    store.link_or_create(
        user_id=2,
        source='lastfm',
        source_key='l1',
        played_at=f'{today.isoformat()}T21:15:00Z',
        artist='B',
        title='U',
    )
    store.link_or_create(
        user_id=1,
        source='downtify',
        source_key='future',
        played_at=f'{(today + timedelta(days=1)).isoformat()}T21:15:00Z',
        artist='C',
        title='Future',
    )

    personal = store.stats(user_id=1, days=7)

    assert personal['period']['total'] == 1
    assert personal['unique']['tracks'] == 1
    assert store.stats(user_id=0, days=7)['period']['total'] == 2


def test_day_plays_returns_exact_scoped_total_and_capped_rows(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    for index in range(3):
        store.link_or_create(
            user_id=1,
            source='spotify',
            source_key=f's{index}',
            played_at=f'2026-11-20T2{index}:15:00Z',
            artist='A',
            title=f'T{index}',
        )
    store.link_or_create(
        user_id=2,
        source='lastfm',
        source_key='other-user',
        played_at='2026-11-20T23:15:00Z',
        artist='B',
        title='Other',
    )

    day = store.day_plays('2026-11-20', user_id=1, limit=2)

    assert day['date'] == '2026-11-20'
    assert day['total'] == 3
    assert len(day['plays']) == 2
    assert day['plays'][0]['at'] == '2026-11-20T22:15:00Z'
    assert all(row['date'] == '2026-11-20' for row in day['plays'])
