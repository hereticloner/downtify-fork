import sqlite3
from datetime import datetime, timezone

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
