from downtify import lastfm_history, spotify_history
from downtify.activity import ActivityLog
from downtify.listening_history import ListeningStore


def test_activity_record_returns_inserted_id(tmp_path):
    log = ActivityLog(tmp_path / 'activity.db')
    activity_id = log.record('playback', user_id=1, summary='A - T')
    assert isinstance(activity_id, int)
    assert log.entries(user_id=1)['entries'][0]['id'] == activity_id


def test_backfill_activity_is_idempotent_and_user_scoped(tmp_path):
    db = tmp_path / 'activity.db'
    log = ActivityLog(db)
    log.record(
        'playback',
        user_id=1,
        summary='A - T',
        detail={'track': {'title': 'T', 'artist': 'A', 'track_id': 's1'}},
    )
    log.record(
        'playback',
        user_id=2,
        summary='B - U',
        detail={'track': {'title': 'U', 'artist': 'B'}},
    )
    log.record('download', user_id=1, summary='ignored')
    store = ListeningStore(db)
    assert store.backfill_activity(log) == 2
    assert store.backfill_activity(log) == 0
    assert store.stats(user_id=1)['total'] == 1
    assert store.stats(user_id=0)['total'] == 2


def test_forget_user_also_removes_raw_provider_rows(tmp_path):
    db = tmp_path / 'activity.db'
    spotify_history.save_recently_played(
        db,
        [
            {
                'played_at': '2026-11-25T20:15:00Z',
                'spotify_track_id': 's1',
                'track_name': 'T',
                'artist_name': 'A',
            }
        ],
        user_id=1,
    )
    lastfm_history.save_recent_tracks(
        db,
        [
            {
                'played_at': '2026-11-25T21:15:00+00:00',
                'uts': 1795631700,
                'artist_name': 'B',
                'track_name': 'U',
            }
        ],
        user_id=1,
    )
    store = ListeningStore(db)
    spotify_history.link_pending(db, store, user_id=1)
    lastfm_history.link_pending(db, store, user_id=1)
    store.forget_user(1)
    assert spotify_history.count_plays(db) == 0
    assert lastfm_history.count_plays(db) == 0
    assert store.stats(user_id=0)['total'] == 0
