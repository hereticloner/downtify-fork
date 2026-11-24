from __future__ import annotations

from downtify.download_failures import DownloadFailureStore


def test_record_merges_attempts_and_context(tmp_path):
    store = DownloadFailureStore(tmp_path / 'library.db')
    song = {'song_id': 'track-1', 'name': 'One', 'artist': 'A'}

    first = store.record(
        song_id='track-1',
        song=song,
        message='No audio match',
        code='no_audio_match',
        provider='youtube',
        playlist_name='First',
        user_ids=[1],
    )
    second = store.record(
        song_id='track-1',
        song=song,
        message='No audio match',
        code='no_audio_match',
        provider='youtube',
        playlist_name='Second',
        user_ids=[2],
    )

    assert first['attempts'] == 1
    assert second['attempts'] == 2
    rows = store.list()
    assert len(rows) == 1
    assert rows[0]['playlists'] == ['First', 'Second']
    assert rows[0]['user_ids'] == [1, 2]
    assert rows[0]['song']['name'] == 'One'


def test_resolve_is_idempotent_and_hidden_by_default(tmp_path):
    store = DownloadFailureStore(tmp_path / 'library.db')
    store.record(song_id='track-1', song={'name': 'One'}, message='failed')

    assert store.resolve('track-1') is True
    assert store.resolve('track-1') is False
    assert store.list() == []
    assert len(store.list(include_resolved=True)) == 1


def test_clear_only_removes_resolved_rows(tmp_path):
    store = DownloadFailureStore(tmp_path / 'library.db')
    for song_id in ('open', 'done'):
        store.record(song_id=song_id, song={'name': song_id}, message='failed')
    store.resolve('done')

    assert store.clear() == 1
    assert [row['song_id'] for row in store.list()] == ['open']
    assert [row['song_id'] for row in store.list(include_resolved=True)] == [
        'open'
    ]


def test_forget_song_removes_the_row(tmp_path):
    store = DownloadFailureStore(tmp_path / 'library.db')
    store.record(song_id='track-1', song={'name': 'One'}, message='failed')

    assert store.forget_song('track-1') is True
    assert store.forget_song('track-1') is False
    assert store.list(include_resolved=True) == []
