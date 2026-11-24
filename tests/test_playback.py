from __future__ import annotations

from downtify import playback as playback_mod
from downtify.playback import PlaybackStore


def test_positions_are_user_scoped(tmp_path):
    store = PlaybackStore(tmp_path / 'playback.db')
    track = {'file': 'A - One.mp3', 'title': 'One', 'duration': 100}
    store.report(
        user_id=1,
        device_id='web',
        player='tab',
        state='paused',
        track=track,
        position=42,
    )

    assert store.latest(1)['position'] == 42
    assert store.latest(2) is None


def test_heartbeats_count_unique_seconds_once(tmp_path):
    store = PlaybackStore(tmp_path / 'playback.db')
    track = {'file': 'A - One.mp3', 'duration': 200}
    for position in (0, 30, 60):
        store.report(
            user_id=1,
            device_id='web',
            player='tab',
            state='playing',
            track=track,
            position=position,
        )

    assert store.summary(1)['seconds'] == 60
    assert store.summary(1)['plays'] == 1


def test_late_or_duplicate_heartbeat_does_not_inflate_seconds(tmp_path):
    store = PlaybackStore(tmp_path / 'playback.db')
    track = {'file': 'A - One.mp3', 'duration': 200}
    for position in (0, 100, 100):
        store.report(
            user_id=1,
            device_id='web',
            player='tab',
            state='playing',
            track=track,
            position=position,
        )

    assert store.summary(1)['seconds'] == 0


def test_seek_jump_is_not_counted_as_listening(tmp_path):
    store = PlaybackStore(tmp_path / 'playback.db')
    track = {'file': 'A - One.mp3', 'duration': 200}
    store.report(
        user_id=1,
        device_id='web',
        player='tab',
        state='playing',
        track=track,
        position=0,
    )
    store.report(
        user_id=1,
        device_id='web',
        player='tab',
        state='playing',
        track=track,
        position=30,
        seek=True,
    )
    store.report(
        user_id=1,
        device_id='web',
        player='tab',
        state='playing',
        track=track,
        position=60,
    )

    assert store.summary(1)['seconds'] == 30


def test_empty_stop_keeps_the_last_position(tmp_path):
    store = PlaybackStore(tmp_path / 'playback.db')
    track = {'file': 'A - One.mp3', 'duration': 100}
    store.report(
        user_id=1,
        device_id='web',
        player='tab',
        state='playing',
        track=track,
        position=42,
    )
    store.report(
        user_id=1,
        device_id='web',
        player='tab',
        state='stopped',
        track={},
        position=0,
    )

    latest = store.latest(1)
    assert latest['track']['file'] == 'A - One.mp3'
    assert latest['position'] == 42
    assert latest['state'] == 'stopped'


def test_completion_is_counted_once(tmp_path):
    store = PlaybackStore(tmp_path / 'playback.db')
    track = {'file': 'A - One.mp3', 'duration': 100}
    for position in (0, 95, 95):
        store.report(
            user_id=1,
            device_id='web',
            player='tab',
            state='playing',
            track=track,
            position=position,
        )

    assert store.summary(1)['completions'] == 1


def test_short_stop_is_counted_as_skip(tmp_path, monkeypatch):
    stamps = iter([
        '2026-11-24T10:00:00+00:00',
        '2026-11-24T10:00:05+00:00',
    ])
    monkeypatch.setattr(playback_mod, '_now', lambda: next(stamps))
    store = PlaybackStore(tmp_path / 'playback.db')
    track = {'file': 'A - One.mp3', 'duration': 100}
    store.report(
        user_id=1,
        device_id='web',
        player='tab',
        state='playing',
        track=track,
        position=0,
    )
    store.report(
        user_id=1,
        device_id='web',
        player='tab',
        state='stopped',
        track=track,
        position=10,
    )

    assert store.summary(1)['skips'] == 1


def test_summary_respects_period(tmp_path):
    store = PlaybackStore(tmp_path / 'playback.db')
    with store._connect() as conn:
        conn.execute(
            'INSERT INTO playback_daily '
            '(user_id, day, seconds, plays, completions, skips) '
            "VALUES (1, '2000-01-01', 99, 1, 0, 0)"
        )
    track = {'file': 'A - One.mp3', 'duration': 100}
    store.report(
        user_id=1,
        device_id='web',
        player='tab',
        state='playing',
        track=track,
        position=0,
    )

    assert store.summary(1, days=7)['seconds'] == 0
    assert store.summary(1, days=30)['plays'] == 1


def test_positions_and_forget_user(tmp_path):
    store = PlaybackStore(tmp_path / 'playback.db')
    for file in ('A - One.mp3', 'A - Two.mp3'):
        store.report(
            user_id=1,
            device_id='web',
            player='tab',
            state='paused',
            track={'file': file, 'duration': 100},
            position=10,
        )

    assert len(store.positions(1)) == 2
    assert store.latest(1)['track']['file'] == 'A - Two.mp3'
    store.forget_user(1)
    assert store.positions(1) == []
    assert store.latest(1) is None


def test_prune_removes_old_playback_rows(tmp_path):
    store = PlaybackStore(tmp_path / 'playback.db')
    track = {'file': 'A - One.mp3', 'duration': 100}
    store.report(
        user_id=1,
        device_id='web',
        player='tab',
        state='paused',
        track=track,
        position=10,
    )
    with store._connect() as conn:
        conn.execute(
            'INSERT INTO playback_positions '
            '(user_id, device_id, player, track_key, track_json, position, '
            'duration, state, started_at, updated_at) '
            "VALUES (1, 'old', 'tab', 'old', '{}', 0, 0, 'paused', "
            "'2000-01-01T00:00:00+00:00', '2000-01-01T00:00:00+00:00')"
        )
        conn.execute(
            'INSERT INTO playback_events '
            '(user_id, device_id, player, track_key, track_json, kind, '
            'position, duration, seconds, at) '
            "VALUES (1, 'old', 'tab', 'old', '{}', 'start', 0, 0, 0, "
            "'2000-01-01T00:00:00+00:00')"
        )
        conn.execute(
            'INSERT INTO playback_daily '
            '(user_id, day, seconds, plays, completions, skips) '
            "VALUES (1, '2000-01-01', 0, 1, 0, 0)"
        )

    assert store.prune(days=30) == 3
    assert len(store.positions(1)) == 1


def test_out_of_order_heartbeats_do_not_rewind_or_double_count(tmp_path):
    store = PlaybackStore(tmp_path / 'playback.db')
    track = {'file': 'A - One.mp3', 'duration': 200}
    for position in (0, 30, 60, 45, 75):
        store.report(
            user_id=1,
            device_id='web',
            player='tab',
            state='playing',
            track=track,
            position=position,
        )

    assert store.summary(1)['seconds'] == 75
    assert store.latest(1)['position'] == 75


def test_first_report_at_completion_counts_once(tmp_path):
    store = PlaybackStore(tmp_path / 'playback.db')
    track = {'file': 'A - One.mp3', 'duration': 100}
    for _ in range(3):
        store.report(
            user_id=1,
            device_id='web',
            player='tab',
            state='playing',
            track=track,
            position=95,
        )

    assert store.summary(1)['completions'] == 1


def test_replay_counts_a_new_session_without_counting_seconds_twice(tmp_path):
    store = PlaybackStore(tmp_path / 'playback.db')
    track = {'file': 'A - One.mp3', 'duration': 100}
    for position in (0, 30, 60, 90):
        store.report(
            user_id=1,
            device_id='web',
            player='tab',
            state='playing',
            track=track,
            position=position,
        )
    store.report(
        user_id=1,
        device_id='web',
        player='tab',
        state='playing',
        track=track,
        position=0,
        seek=True,
    )
    for position in (30, 60, 90):
        store.report(
            user_id=1,
            device_id='web',
            player='tab',
            state='playing',
            track=track,
            position=position,
        )

    summary = store.summary(1)
    assert summary['seconds'] == 90
    assert summary['plays'] == 2
    assert summary['completions'] == 2


def test_switching_tracks_early_counts_previous_as_skip(tmp_path, monkeypatch):
    stamps = iter([
        '2026-11-24T10:00:00+00:00',
        '2026-11-24T10:00:05+00:00',
    ])
    monkeypatch.setattr(playback_mod, '_now', lambda: next(stamps))
    store = PlaybackStore(tmp_path / 'playback.db')
    store.report(
        user_id=1,
        device_id='web',
        player='tab',
        state='playing',
        track={'file': 'A - One.mp3', 'duration': 100},
        position=0,
    )
    store.report(
        user_id=1,
        device_id='web',
        player='tab',
        state='playing',
        track={'file': 'A - Two.mp3', 'duration': 100},
        position=0,
    )

    assert store.summary(1)['plays'] == 2
    assert store.summary(1)['skips'] == 1
