import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from downtify import lastfm_history, spotify_history
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


def test_offset_timestamp_is_stored_as_utc_for_stats_and_day_queries(tmp_path):
    db = tmp_path / 'activity.db'
    store = ListeningStore(db)
    event_id, _ = store.link_or_create(
        user_id=1,
        source='lastfm',
        source_key='offset',
        played_at='2026-11-21T23:30:00-02:00',
        artist='A',
        title='T',
    )
    with sqlite3.connect(db) as conn:
        played_at = conn.execute(
            'SELECT played_at FROM listening_events WHERE id=?', (event_id,)
        ).fetchone()[0]
    assert played_at == '2026-11-22T01:30:00+00:00'
    assert store.day_plays('2026-11-22', user_id=1)['total'] == 1


def test_period_total_does_not_depend_on_sqlite_hour_parsing(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    today = datetime.now(timezone.utc).date().isoformat()
    store.link_or_create(
        user_id=1,
        source='lastfm',
        source_key='offset-seconds',
        played_at=f'{today}T20:15:00+03:00:30',
        artist='A',
        title='T',
    )

    data = store.stats(user_id=1, days=7)

    assert data['period']['total'] == 1
    assert data['track_time']['plays_without_duration'] == 1
    assert sum(data['patterns']['by_hour']) == 1
    assert store.day_plays(today, user_id=1)['total'] == 1
    assert data['daily'] == [{'date': today, 'count': 1}]


def test_period_window_includes_midnight_and_last_second(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=6)
    for source_key, played_at in (
        ('start', f'{start.isoformat()}T00:00:00Z'),
        ('end', f'{today.isoformat()}T23:59:59Z'),
        ('before', f'{(start - timedelta(days=1)).isoformat()}T23:59:59Z'),
        ('future', f'{(today + timedelta(days=1)).isoformat()}T00:00:00Z'),
    ):
        store.link_or_create(
            user_id=1,
            source='lastfm',
            source_key=source_key,
            played_at=played_at,
            artist='A',
            title=source_key,
        )

    assert store.stats(user_id=1, days=7)['period']['total'] == 2


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
        source='lastfm',
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
    assert personal['top_tracks'] == [
        {
            'summary': 'A - T',
            'artist': 'A',
            'title': 'T',
            'album': '',
            'count': 1,
        }
    ]
    assert personal['daily'] == [{'date': today, 'count': 1}]
    assert personal['top_contexts'] == [{'context': 'Mix', 'count': 1}]
    assert personal['recent'][0]['source'] == 'lastfm'
    assert store.stats(user_id=0)['total'] == 2


def test_stats_excludes_spotify_only_but_keeps_lastfm_and_downtify(tmp_path):
    db = tmp_path / 'activity.db'
    store = ListeningStore(db)
    today = datetime.now(timezone.utc).date().isoformat()

    store.link_or_create(
        user_id=1,
        source='spotify',
        source_key='spotify:only',
        played_at=f'{today}T01:00:00Z',
        artist='Solo',
        title='Spotify Only',
        duration_ms=600000,
        context='spotify:playlist:ignored',
        context_type='playlist',
    )
    store.link_or_create(
        user_id=1,
        source='lastfm',
        source_key='lastfm:only',
        played_at=f'{today}T02:00:00Z',
        artist='Last',
        title='FM Only',
    )
    legacy_id, _ = store.link_or_create(
        user_id=1,
        source='spotify',
        source_key='spotify:legacy',
        played_at='2026-11-25T20:15:00Z',
        artist='Legacy',
        title='Old',
        duration_ms=180000,
    )
    _link_legacy_lastfm_row(db, legacy_id)
    assert store.reconcile_lastfm_sources() == 1
    store.link_or_create(
        user_id=1,
        source='downtify',
        source_key='activity:1',
        played_at=f'{today}T04:00:00Z',
        artist='Local',
        title='Play',
        duration_ms=120000,
    )
    store.link_or_create(
        user_id=1,
        source='spotify',
        source_key='spotify:linked',
        played_at=f'{today}T04:00:30Z',
        artist='Local',
        title='Play',
    )

    data = store.stats(user_id=1)

    assert data['total'] == 3
    assert data['profile']['by_source'] == {
        'downtify': 1,
        'spotify': 0,
        'lastfm': 2,
    }
    assert {row['source'] for row in data['recent']} == {'downtify', 'lastfm'}
    assert 'Spotify Only' not in {row['summary'] for row in data['top_tracks']}
    assert 'spotify:playlist:ignored' not in {
        row['context'] for row in data['top_contexts']
    }
    assert data['track_time']['seconds'] == 120
    # The excluded Spotify-only canonical row is still stored, untouched.
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            'SELECT duration_ms, context FROM listening_events '
            "WHERE source='spotify'"
        ).fetchone()
    assert row == (600000, 'spotify:playlist:ignored')


def test_day_and_pattern_details_use_the_same_stats_source_filter(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    today = datetime.now(timezone.utc).date().isoformat()
    for user_id, source, key, minute, title in (
        (1, 'spotify', 'spotify:day', 10, 'Ignored'),
        (1, 'lastfm', 'lastfm:day', 20, 'Kept'),
        (2, 'spotify', 'spotify:other', 30, 'Other User'),
    ):
        store.link_or_create(
            user_id=user_id,
            source=source,
            source_key=key,
            played_at=f'{today}T14:{minute:02d}:00Z',
            artist=source,
            title=title,
        )

    personal_day = store.day_plays(today, user_id=1)
    personal_detail = store.pattern_detail(1, 7, 'hour', 14)
    server_day = store.day_plays(today)
    server_detail = store.pattern_detail(0, 7, 'hour', 14)

    for day in (personal_day, server_day):
        assert day['total'] == 1
        assert [row['source'] for row in day['plays']] == ['lastfm']
        assert [row['summary'] for row in day['plays']] == ['lastfm - Kept']
    for detail in (personal_detail, server_detail):
        assert detail['total'] == 1
        assert detail['by_source'] == {
            'downtify': 0,
            'spotify': 0,
            'lastfm': 1,
        }
        assert [row['source'] for row in detail['recent']] == ['lastfm']
    assert store.stats(user_id=1, days=7)['patterns']['by_hour'][14] == 1


def test_all_time_profile_aggregates_are_canonical_and_user_scoped(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    store.link_or_create(
        user_id=1,
        source='lastfm',
        source_key='profile:s1',
        played_at='2026-10-08T10:00:00Z',
        artist='Artist A',
        title='Track A',
        album='Album A',
    )
    store.link_or_create(
        user_id=1,
        source='lastfm',
        source_key='profile:l1',
        played_at='2026-11-20T10:00:00Z',
        artist='Artist A',
        title='Track B',
        album='Album A',
    )
    store.link_or_create(
        user_id=2,
        source='downtify',
        source_key='profile:other',
        played_at='2026-11-21T10:00:00Z',
        artist='Other',
        title='Hidden',
        album='Other album',
    )

    data = store.stats(user_id=1, days=7)

    assert data['total'] == 2
    assert data['profile'] == {
        'first_at': '2026-10-08T10:00:00Z',
        'last_at': '2026-11-20T10:00:00Z',
        'unique': {'tracks': 2, 'artists': 1, 'albums': 1},
        'by_source': {'downtify': 0, 'spotify': 0, 'lastfm': 2},
        'top_artists': [{'artist': 'Artist A', 'count': 2}],
        'top_albums': [{'album': 'Album A', 'artist': 'Artist A', 'count': 2}],
        'weeks': data['profile']['weeks'],
    }
    assert len(data['profile']['weeks']) == 4
    assert data['top_tracks'][0] == {
        'summary': 'Artist A - Track A',
        'artist': 'Artist A',
        'title': 'Track A',
        'album': 'Album A',
        'count': 1,
    }
    assert data['recent'][0] == {
        'at': '2026-11-20T10:00:00Z',
        'date': '2026-11-20',
        'summary': 'Artist A - Track B',
        'artist': 'Artist A',
        'title': 'Track B',
        'album': 'Album A',
        'context': '',
        'context_type': '',
        'source': 'lastfm',
    }


def test_profile_weeks_are_four_consecutive_utc_buckets(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    today = datetime.now(timezone.utc).date()
    for index, offset in enumerate((0, 6, 7, 13, 14, 20, 21, 27)):
        store.link_or_create(
            user_id=1,
            source='lastfm',
            source_key=f'week:{index}',
            played_at=f'{(today - timedelta(days=offset)).isoformat()}T12:00:00Z',
            artist='A',
            title=f'T{index}',
        )

    weeks = store.stats(user_id=1, days=7)['profile']['weeks']

    assert [row['count'] for row in weeks] == [2, 2, 2, 2]
    assert weeks[0]['start'] == (today - timedelta(days=27)).isoformat()
    assert weeks[-1]['end'] == today.isoformat()
    for previous, current in zip(weeks, weeks[1:]):
        assert (
            datetime.fromisoformat(current['start']).date()
            - datetime.fromisoformat(previous['end']).date()
        ).days == 1


def test_profile_top_albums_keep_artists_separate(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    for index, (artist, album) in enumerate((
        ('Artist A', 'Same Album'),
        ('Artist B', 'Same Album'),
    )):
        store.link_or_create(
            user_id=1,
            source='lastfm',
            source_key=f'album-artist:{index}',
            played_at=f'2026-11-2{index}T10:00:00Z',
            artist=artist,
            title=f'Track {index}',
            album=album,
        )

    assert store.stats(user_id=1)['profile']['top_albums'] == [
        {'album': 'Same Album', 'artist': 'Artist A', 'count': 1},
        {'album': 'Same Album', 'artist': 'Artist B', 'count': 1},
    ]


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
        'by_source': {'downtify': 0, 'spotify': 0, 'lastfm': 1},
    }


def test_period_aggregates_report_unique_duration_and_utc_patterns(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    today = datetime.now(timezone.utc).date()
    store.link_or_create(
        user_id=1,
        source='downtify',
        source_key='activity:duration',
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
    assert isinstance(data['track_time']['seconds'], int)
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
        source='lastfm',
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
            source='lastfm',
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


def test_pattern_detail_matches_hour_bar_and_uses_canonical_sources(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    today = datetime.now(timezone.utc).date().isoformat()
    for index in range(2):
        store.link_or_create(
            user_id=1,
            source='lastfm',
            source_key=f'hour:{index}',
            played_at=f'{today}T14:15:00Z',
            artist='A',
            title=f'T{index}',
        )
    store.link_or_create(
        user_id=1,
        source='lastfm',
        source_key='other-hour',
        played_at=f'{today}T15:15:00Z',
        artist='B',
        title='Other',
    )

    detail = store.pattern_detail(1, 7, 'hour', 14)
    stats = store.stats(1, days=7)

    assert detail['total'] == stats['patterns']['by_hour'][14] == 2
    assert detail['by_source'] == {'downtify': 0, 'spotify': 0, 'lastfm': 2}
    assert len(detail['top_tracks']) == 2
    assert detail['top_artists'] == [{'artist': 'A', 'count': 2}]
    assert len(detail['recent']) == 2
    assert detail['truncated'] is False


def test_pattern_detail_supports_weekday_and_utc_boundaries(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    today = datetime.now(timezone.utc).date()
    weekday = int(today.strftime('%w'))
    for key, at in (
        ('midnight', f'{today.isoformat()}T00:00:00Z'),
        ('last-second', f'{today.isoformat()}T23:59:59Z'),
    ):
        store.link_or_create(
            user_id=1,
            source='lastfm',
            source_key=key,
            played_at=at,
            artist='A',
            title=key,
        )

    assert store.pattern_detail(1, 7, 'hour', 0)['total'] == 1
    assert store.pattern_detail(1, 7, 'hour', 23)['total'] == 1
    assert store.pattern_detail(1, 7, 'weekday', weekday)['total'] == 2


def test_pattern_detail_is_scoped_capped_and_truncated(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    today = datetime.now(timezone.utc).date().isoformat()
    for index in range(55):
        store.link_or_create(
            user_id=1,
            source='lastfm',
            source_key=f'user1:{index}',
            played_at=f'{today}T14:15:00Z',
            artist='A',
            title=f'T{index}',
        )
    store.link_or_create(
        user_id=2,
        source='lastfm',
        source_key='user2',
        played_at=f'{today}T14:15:00Z',
        artist='B',
        title='Other',
    )

    personal = store.pattern_detail(1, 7, 'hour', 14, recent_limit=50)
    server = store.pattern_detail(0, 7, 'hour', 14, recent_limit=50)

    assert personal['total'] == 55
    assert len(personal['recent']) == 50
    assert personal['truncated'] is True
    assert server['total'] == 56


def test_pattern_detail_empty_shape_and_validation(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')

    assert store.pattern_detail(1, 7, 'hour', 14) == {
        'kind': 'hour',
        'bucket': 14,
        'total': 0,
        'by_source': {'downtify': 0, 'spotify': 0, 'lastfm': 0},
        'top_tracks': [],
        'top_artists': [],
        'recent': [],
        'truncated': False,
    }
    with pytest.raises(ValueError, match='out of range'):
        store.pattern_detail(1, 7, 'hour', 24)
    with pytest.raises(ValueError, match='kind must be'):
        store.pattern_detail(1, 7, 'month', 1)


def _link_spotify_observation(
    db,
    store,
    event_id,
    *,
    album='Spotify Album',
    context_uri='spotify:playlist:abc',
):
    spotify_history.save_recently_played(
        db,
        [
            {
                'played_at': '2026-11-25T20:15:00Z',
                'spotify_track_id': 's1',
                'track_name': 'T',
                'artist_name': 'A',
                'album_name': album,
                'context': {
                    'type': 'playlist',
                    'uri': context_uri,
                },
            }
        ],
        user_id=1,
    )
    assert spotify_history.link_pending(db, store, user_id=1) == 1
    with sqlite3.connect(db) as conn:
        assert (
            conn.execute(
                'SELECT listening_event_id FROM spotify_recently_played'
            ).fetchone()[0]
            == event_id
        )


def _canonical_row(db):
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        return dict(
            conn.execute(
                'SELECT source, played_at, album, context, context_type '
                'FROM listening_events WHERE id=1'
            ).fetchone()
        )


def test_enrichment_fills_only_blank_canonical_metadata(tmp_path):
    db = tmp_path / 'activity.db'
    store = ListeningStore(db)
    event_id, _ = store.link_or_create(
        user_id=1,
        source='downtify',
        source_key='activity:1',
        played_at='2026-11-25T20:15:00Z',
        artist='A',
        title='T',
    )
    _link_spotify_observation(db, store, event_id)

    assert store.enrich_from_raw() == 1

    row = _canonical_row(db)
    assert row['album'] == 'Spotify Album'
    assert row['context'] == 'spotify:playlist:abc'
    assert row['context_type'] == 'playlist'
    assert row['source'] == 'downtify'
    assert row['played_at'] == '2026-11-25T20:15:00Z'
    assert store.stats(user_id=1)['total'] == 1


def test_enrichment_is_idempotent_and_preserves_known_values(tmp_path):
    db = tmp_path / 'activity.db'
    store = ListeningStore(db)
    event_id, _ = store.link_or_create(
        user_id=1,
        source='downtify',
        source_key='activity:1',
        played_at='2026-11-25T20:15:00Z',
        artist='A',
        title='T',
        album='Downtify Album',
        context='Downtify Playlist',
        context_type='playlist',
    )
    _link_spotify_observation(db, store, event_id)

    assert store.enrich_from_raw() == 0
    assert store.enrich_from_raw() == 0
    assert _canonical_row(db)['context'] == 'Downtify Playlist'
    assert _canonical_row(db)['album'] == 'Downtify Album'


def test_enrichment_fills_lastfm_album_without_changing_source(tmp_path):
    db = tmp_path / 'activity.db'
    store = ListeningStore(db)
    event_id, _ = store.link_or_create(
        user_id=1,
        source='downtify',
        source_key='activity:1',
        played_at='2026-11-25T20:15:00Z',
        artist='A',
        title='T',
    )
    lastfm_history.save_recent_tracks(
        db,
        [
            {
                'played_at': '2026-11-25T20:15:00+00:00',
                'uts': 1794166500,
                'artist_name': 'A',
                'track_name': 'T',
                'album_name': 'Last.fm Album',
            }
        ],
        user_id=1,
    )
    assert lastfm_history.link_pending(db, store, user_id=1) == 1

    assert store.enrich_from_raw() == 1

    row = _canonical_row(db)
    assert row['album'] == 'Last.fm Album'
    assert row['source'] == 'downtify'


def test_lastfm_promotes_spotify_and_downtify_still_wins(tmp_path):
    db = tmp_path / 'activity.db'
    store = ListeningStore(db)
    event_id, created = store.link_or_create(
        user_id=1,
        source='spotify',
        source_key='spotify:1',
        played_at='2026-11-25T20:15:00Z',
        artist='A',
        title='Song',
    )
    assert (event_id, created) == (1, True)

    promoted, created = store.link_or_create(
        user_id=1,
        source='lastfm',
        source_key='lastfm:1',
        played_at='2026-11-25T20:18:00Z',
        artist='A',
        title='SONG',
    )
    assert (promoted, created) == (event_id, False)
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            'SELECT source, source_key, played_at, title, artist, album '
            'FROM listening_events WHERE id=?',
            (event_id,),
        ).fetchone()
    assert row == (
        'lastfm',
        'lastfm:1',
        '2026-11-25T20:18:00Z',
        'SONG',
        'A',
        '',
    )
    assert store.stats(user_id=1)['total'] == 1

    local, created = store.link_or_create(
        user_id=1,
        source='downtify',
        source_key='activity:9',
        played_at='2026-11-25T20:16:00Z',
        artist='A',
        title='Song',
    )
    assert (local, created) == (event_id, False)
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            'SELECT source, source_key, played_at, title FROM listening_events '
            'WHERE id=?',
            (event_id,),
        ).fetchone()
    assert row == ('downtify', 'activity:9', '2026-11-25T20:16:00Z', 'Song')
    assert store.stats(user_id=1)['total'] == 1


def _link_legacy_lastfm_row(db, event_id, *, legacy_empty_key=False):
    """Attach a Last.fm raw observation to an existing canonical event."""

    lastfm_history.save_recent_tracks(
        db,
        [
            {
                'played_at': '2026-11-25T20:18:00+00:00',
                'uts': 1795633080,
                'artist_name': 'Last.fm Artist',
                'track_name': 'Last.fm Title',
                'album_name': 'Last.fm Album',
            }
        ],
        user_id=1,
    )
    with sqlite3.connect(db) as conn:
        raw = conn.execute(
            'SELECT source_key FROM lastfm_recent_tracks'
        ).fetchone()[0]
        conn.execute(
            'INSERT INTO listening_event_sources (event_id, source, source_key) '
            'VALUES (?, ?, ?)',
            (event_id, 'lastfm', '' if legacy_empty_key else raw),
        )
        conn.execute(
            'UPDATE lastfm_recent_tracks SET listening_event_id=?', (event_id,)
        )
    return raw


@pytest.mark.parametrize('legacy_empty_key', [False, True])
def test_reconcile_lastfm_sources_upgrades_legacy_rows_idempotently(
    tmp_path, legacy_empty_key
):
    db = tmp_path / 'activity.db'
    store = ListeningStore(db)
    event_id, _ = store.link_or_create(
        user_id=1,
        source='spotify',
        source_key='spotify:1',
        played_at='2026-11-25T20:15:00Z',
        artist='Spotify Artist',
        title='Spotify Title',
        album='Spotify Album',
        duration_ms=180000,
        context='spotify:playlist:abc',
        context_type='playlist',
    )
    raw_key = _link_legacy_lastfm_row(
        db, event_id, legacy_empty_key=legacy_empty_key
    )
    with sqlite3.connect(db) as conn:
        before_event = conn.execute(
            'SELECT id, identity_key, match_key FROM listening_events WHERE id=?',
            (event_id,),
        ).fetchone()
        before_links = conn.execute(
            'SELECT event_id, source, source_key FROM listening_event_sources '
            'WHERE event_id=? ORDER BY source',
            (event_id,),
        ).fetchall()
        before_raw = conn.execute(
            'SELECT * FROM lastfm_recent_tracks'
        ).fetchone()

    assert store.reconcile_lastfm_sources() == 1
    assert store.reconcile_lastfm_sources() == 0

    with sqlite3.connect(db) as conn:
        row = conn.execute(
            'SELECT id, identity_key, match_key, source, source_key, played_at, '
            'title, artist, album, duration_ms, context, context_type '
            'FROM listening_events WHERE id=?',
            (event_id,),
        ).fetchone()
        after_links = conn.execute(
            'SELECT event_id, source, source_key FROM listening_event_sources '
            'WHERE event_id=? ORDER BY source',
            (event_id,),
        ).fetchall()
        after_raw = conn.execute(
            'SELECT * FROM lastfm_recent_tracks'
        ).fetchone()
    assert row[:3] == before_event
    assert (
        row[3],
        row[4],
        row[5],
        row[6],
        row[7],
        row[8],
        row[9],
        row[10],
        row[11],
    ) == (
        'lastfm',
        raw_key,
        '2026-11-25T20:18:00+00:00',
        'Last.fm Title',
        'Last.fm Artist',
        'Last.fm Album',
        0,
        '',
        '',
    )
    assert after_links == before_links
    assert after_raw == before_raw


@pytest.mark.parametrize('legacy_empty_key', [False, True])
def test_reconcile_lastfm_sources_keeps_downtify_links(
    tmp_path, legacy_empty_key
):
    db = tmp_path / 'activity.db'
    store = ListeningStore(db)
    event_id, _ = store.link_or_create(
        user_id=1,
        source='downtify',
        source_key='activity:1',
        played_at='2026-11-25T20:15:00Z',
        artist='A',
        title='T',
        album='Downtify Album',
        duration_ms=200000,
        context='Downtify Playlist',
        context_type='playlist',
    )
    _link_legacy_lastfm_row(db, event_id, legacy_empty_key=legacy_empty_key)

    assert store.reconcile_lastfm_sources() == 0
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            'SELECT source, source_key, played_at, title, artist, album, '
            'duration_ms, context, context_type FROM listening_events WHERE id=?',
            (event_id,),
        ).fetchone()
    assert row == (
        'downtify',
        'activity:1',
        '2026-11-25T20:15:00Z',
        'T',
        'A',
        'Downtify Album',
        200000,
        'Downtify Playlist',
        'playlist',
    )
