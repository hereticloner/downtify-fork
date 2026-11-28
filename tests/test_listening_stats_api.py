import sqlite3

import pytest

from downtify import lastfm_history, listening_history, spotify_history
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


@pytest.mark.asyncio
async def test_bootstrap_links_all_pending_rows_in_batches(
    tmp_path, monkeypatch
):
    db = tmp_path / 'activity.db'
    rows = [
        {
            'played_at': '2026-11-25T20:15:00Z',
            'spotify_track_id': f's{index}',
            'track_name': f'T{index}',
            'artist_name': 'A',
        }
        for index in range(250)
    ]
    assert spotify_history.save_recently_played(db, rows, user_id=1) == 250
    activity = ActivityLog(db)
    activity.record(
        'playback',
        user_id=1,
        summary='Z - X',
        detail={'track': {'title': 'X', 'artist': 'Z'}},
    )
    store = ListeningStore(db)

    async def no_pause(_seconds):
        return None

    monkeypatch.setattr(listening_history.asyncio, 'sleep', no_pause)
    linked = await listening_history.bootstrap_listening_history(
        activity,
        db,
        store,
        user_id=1,
        batch_size=100,
    )
    assert linked == 250
    # The Spotify-only rows stay stored, but Stats counts only the local play.
    assert spotify_history.count_plays(db) == 250
    stats = store.stats(user_id=1)
    assert stats['total'] == 1
    assert stats['profile']['by_source']['spotify'] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize('legacy_empty_key', [False, True])
async def test_bootstrap_reconciles_legacy_lastfm_linked_row(
    tmp_path, monkeypatch, legacy_empty_key
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
        raw_key = conn.execute(
            'SELECT source_key FROM lastfm_recent_tracks'
        ).fetchone()[0]
        conn.execute(
            'INSERT INTO listening_event_sources (event_id, source, source_key) '
            'VALUES (?, ?, ?)',
            (event_id, 'lastfm', '' if legacy_empty_key else raw_key),
        )
        conn.execute(
            'UPDATE lastfm_recent_tracks SET listening_event_id=?', (event_id,)
        )
    activity = ActivityLog(db)

    async def no_pause(_seconds):
        return None

    monkeypatch.setattr(listening_history.asyncio, 'sleep', no_pause)
    linked = await listening_history.bootstrap_listening_history(
        activity, db, store, user_id=1
    )

    assert linked == 0
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            'SELECT source, source_key, played_at, title, artist, album, '
            'duration_ms, context, context_type FROM listening_events WHERE id=?',
            (event_id,),
        ).fetchone()
    assert row == (
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
