"""Failing tests first: the smart-collection rule engine.

A rule set is a list of conditions combined with AND. Each rule is
evaluated against one *playlist* of the library: a playlist is a member
when its tracks (and its own added date / total play count) satisfy every
rule. The engine is pure - no disk, no database - so the API layer can
feed it the library snapshot it already has.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from downtify.collection_rules import (
    RuleError,
    normalize_rules,
    playlist_matches,
    resolve_collection,
)


def playlist(
    name: str,
    files: list[str],
    *,
    added: int = 0,
) -> dict:
    return {'name': name, 'files': files, 'added': added}


def track(
    *,
    genre: str = '',
    artist: str = '',
    album: str = '',
    codec: str = '',
    file: str = '',
) -> dict:
    return {
        'file': file,
        'genre': genre,
        'artist': artist,
        'album': album,
        'codec': codec,
    }


TRACKS = {
    'rock/one.mp3': track(
        genre='Rock',
        artist='AC/DC',
        album='Back in Black',
        codec='mp3',
        file='rock/one.mp3',
    ),
    'jazz/two.flac': track(
        genre='Jazz',
        artist='Miles Davis',
        album='Kind of Blue',
        codec='flac',
        file='jazz/two.flac',
    ),
}

PLAYS = {'rock/one.mp3': 12, 'jazz/two.flac': 0}


# ── normalize_rules ─────────────────────────────────────────────────


def test_normalize_empty_is_no_rules() -> None:
    assert normalize_rules(None) == []
    assert normalize_rules([]) == []


def test_normalize_rejects_non_list() -> None:
    with pytest.raises(RuleError):
        normalize_rules({'type': 'genre', 'value': 'Rock'})


def test_normalize_rejects_unknown_type() -> None:
    with pytest.raises(RuleError):
        normalize_rules([{'type': 'bpm', 'value': '120'}])


def test_normalize_added_keeps_valid_range() -> None:
    rules = normalize_rules([
        {'type': 'added', 'from': '2024-01-01', 'to': '2024-12-31'}
    ])
    assert rules == [
        {'type': 'added', 'from': '2024-01-01', 'to': '2024-12-31'}
    ]


def test_normalize_added_needs_a_bound() -> None:
    with pytest.raises(RuleError):
        normalize_rules([{'type': 'added'}])


def test_normalize_added_rejects_bad_date() -> None:
    with pytest.raises(RuleError):
        normalize_rules([{'type': 'added', 'from': 'yesterday'}])


def test_normalize_plays_keeps_bounds_as_ints() -> None:
    rules = normalize_rules([{'type': 'plays', 'min': '2', 'max': 9}])
    assert rules == [{'type': 'plays', 'min': 2, 'max': 9}]


def test_normalize_plays_needs_a_bound() -> None:
    with pytest.raises(RuleError):
        normalize_rules([{'type': 'plays'}])


def test_normalize_plays_rejects_min_above_max() -> None:
    with pytest.raises(RuleError):
        normalize_rules([{'type': 'plays', 'min': 5, 'max': 1}])


def test_normalize_text_rule_needs_a_value() -> None:
    with pytest.raises(RuleError):
        normalize_rules([{'type': 'genre', 'value': '   '}])


def test_normalize_text_rule_trims_the_value() -> None:
    assert normalize_rules([{'type': 'artist', 'value': '  AC/DC '}]) == [
        {'type': 'artist', 'value': 'AC/DC'}
    ]


# ── one rule type at a time ─────────────────────────────────────────


def test_added_rule_selects_a_date_window() -> None:
    inside = int(datetime(2024, 6, 1, tzinfo=timezone.utc).timestamp())
    outside = int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp())
    rules = normalize_rules([
        {'type': 'added', 'from': '2024-05-01', 'to': '2024-07-01'}
    ])
    assert playlist_matches(
        rules, playlist('New', [], added=inside), TRACKS, PLAYS
    )
    assert not playlist_matches(
        rules, playlist('Old', [], added=outside), TRACKS, PLAYS
    )


def test_plays_rule_matches_the_total() -> None:
    rules = normalize_rules([{'type': 'plays', 'min': 1}])
    assert playlist_matches(
        rules, playlist('Liked', ['rock/one.mp3']), TRACKS, PLAYS
    )
    assert not playlist_matches(
        rules, playlist('Silent', ['jazz/two.flac']), TRACKS, PLAYS
    )


def test_plays_rule_max_zero_means_never_played() -> None:
    rules = normalize_rules([{'type': 'plays', 'max': 0}])
    assert playlist_matches(
        rules, playlist('Silent', ['jazz/two.flac']), TRACKS, PLAYS
    )
    assert not playlist_matches(
        rules, playlist('Liked', ['rock/one.mp3']), TRACKS, PLAYS
    )


def test_genre_rule_matches_any_track() -> None:
    rules = normalize_rules([{'type': 'genre', 'value': 'jazz'}])
    assert playlist_matches(
        rules, playlist('Two', ['jazz/two.flac']), TRACKS, PLAYS
    )
    assert not playlist_matches(
        rules, playlist('One', ['rock/one.mp3']), TRACKS, PLAYS
    )


def test_artist_rule_matches_one_artist_of_a_list() -> None:
    tracks = {'a.mp3': track(artist='Foo; Bar', file='a.mp3')}
    rules = normalize_rules([{'type': 'artist', 'value': 'Bar'}])
    assert playlist_matches(rules, playlist('P', ['a.mp3']), tracks, {})
    other = normalize_rules([{'type': 'artist', 'value': 'Baz'}])
    assert not playlist_matches(other, playlist('P', ['a.mp3']), tracks, {})


def test_artist_rule_does_not_substring_match() -> None:
    tracks = {'a.mp3': track(artist='The Rockers', file='a.mp3')}
    rules = normalize_rules([{'type': 'artist', 'value': 'Rock'}])
    assert not playlist_matches(rules, playlist('P', ['a.mp3']), tracks, {})


def test_album_rule_matches_exactly() -> None:
    rules = normalize_rules([{'type': 'album', 'value': 'Kind of Blue'}])
    assert playlist_matches(
        rules, playlist('Jazz', ['jazz/two.flac']), TRACKS, PLAYS
    )
    assert not playlist_matches(
        rules, playlist('Rock', ['rock/one.mp3']), TRACKS, PLAYS
    )


def test_format_rule_matches_codec_or_suffix() -> None:
    rules = normalize_rules([{'type': 'format', 'value': 'FLAC'}])
    assert playlist_matches(
        rules, playlist('Lossless', ['jazz/two.flac']), TRACKS, PLAYS
    )
    assert not playlist_matches(
        rules, playlist('Lossy', ['rock/one.mp3']), TRACKS, PLAYS
    )


def test_format_rule_falls_back_to_the_file_suffix() -> None:
    tracks = {'song.opus': track(file='song.opus')}
    rules = normalize_rules([{'type': 'format', 'value': 'Opus'}])
    assert playlist_matches(rules, playlist('P', ['song.opus']), tracks, {})


# ── combination, empty and union ────────────────────────────────────


def test_rules_are_combined_with_and() -> None:
    rules = normalize_rules([
        {'type': 'genre', 'value': 'Rock'},
        {'type': 'plays', 'min': 10},
    ])
    assert playlist_matches(
        rules, playlist('Both', ['rock/one.mp3']), TRACKS, PLAYS
    )
    assert not playlist_matches(
        rules, playlist('Neither', ['jazz/two.flac']), TRACKS, PLAYS
    )


def test_no_rule_matches_every_playlist() -> None:
    assert playlist_matches([], playlist('P', ['rock/one.mp3']), TRACKS, PLAYS)


def test_empty_result_when_nothing_matches() -> None:
    rules = normalize_rules([{'type': 'genre', 'value': 'Polka'}])
    result = resolve_collection(
        {'version': 1, 'name': 'None', 'playlists': [], 'rules': rules},
        playlists=[playlist('A', ['rock/one.mp3'])],
        tracks=TRACKS,
        play_counts=PLAYS,
    )
    assert result['playlists'] == []
    assert result['computed'] == []


def test_union_keeps_static_members_and_adds_matches() -> None:
    rules = normalize_rules([{'type': 'genre', 'value': 'Jazz'}])
    result = resolve_collection(
        {'version': 1, 'name': 'Mix', 'playlists': ['Rocky'], 'rules': rules},
        playlists=[
            playlist('Rocky', ['rock/one.mp3']),
            playlist('Blue', ['jazz/two.flac']),
        ],
        tracks=TRACKS,
        play_counts=PLAYS,
    )
    assert result['playlists'] == ['Rocky', 'Blue']
    assert result['computed'] == ['Blue']


def test_static_only_collection_is_unchanged() -> None:
    data = {'version': 1, 'name': 'Plain', 'playlists': ['A']}
    assert (
        resolve_collection(data, playlists=[], tracks={}, play_counts={})
        == data
    )


def test_static_member_matching_a_rule_is_not_listed_as_computed() -> None:
    rules = normalize_rules([{'type': 'genre', 'value': 'Jazz'}])
    result = resolve_collection(
        {'version': 1, 'name': 'Mix', 'playlists': ['Blue'], 'rules': rules},
        playlists=[playlist('Blue', ['jazz/two.flac'])],
        tracks=TRACKS,
        play_counts=PLAYS,
    )
    assert result['playlists'] == ['Blue']
    assert result['computed'] == []
