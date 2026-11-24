from __future__ import annotations

from downtify.collection_actions import collection_analysis, collection_tracks


def test_collection_tracks_dedupe_across_playlists_and_keep_order():
    data = {'name': 'Mix', 'playlists': ['A', 'B']}
    playlists = [
        {'name': 'A', 'files': ['one.mp3', 'two.mp3']},
        {'name': 'B', 'files': ['two.mp3', 'three.mp3']},
    ]
    tracks = {
        'one.mp3': {'file': 'one.mp3', 'song_id': 'one', 'title': 'One'},
        'two.mp3': {'file': 'two.mp3', 'song_id': 'two', 'title': 'Two'},
        'three.mp3': {'file': 'three.mp3', 'title': 'Three'},
    }

    result = collection_tracks(data, playlists, tracks)

    assert [track['file'] for track in result] == [
        'one.mp3',
        'two.mp3',
        'three.mp3',
    ]


def test_collection_analysis_counts_unique_tracks_and_missing_files():
    data = {'name': 'Mix', 'playlists': ['A', 'B']}
    playlists = [
        {'name': 'A', 'files': ['one.mp3', 'two.mp3', 'missing.mp3']},
        {'name': 'B', 'files': ['two.mp3', 'three.mp3']},
    ]
    tracks = {
        'one.mp3': {'file': 'one.mp3', 'duration': 100, 'size': 10},
        'two.mp3': {'file': 'two.mp3', 'duration': 200.5, 'size': 20},
        'three.mp3': {'file': 'three.mp3', 'duration': 50, 'size': 30},
    }

    assert collection_analysis(data, playlists, tracks) == {
        'tracks': 3,
        'duration_seconds': 350.5,
        'bytes': 60,
        'missing_tracks': 1,
        'missing_ratio': 0.25,
    }
