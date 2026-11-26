import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

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
        source='spotify',
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
        source='spotify',
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
            source='spotify',
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
