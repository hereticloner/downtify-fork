"""Ownership rows: who put each library file on the server.

The class is the only source of truth for per-user download history
and for hiding other accounts' files from a non-admin library view.
Every test uses a throwaway SQLite database.
"""

from __future__ import annotations

import pytest

from downtify.track_owners import TrackOwners


@pytest.fixture
def owners(tmp_path):
    return TrackOwners(tmp_path / 'library.db')


def test_add_records_each_owner_once(owners):
    assert owners.add('key1', 1, 'Artist/Track.mp3') is True
    assert owners.add('key1', 1, 'Artist/Track.mp3') is False
    assert owners.add('key1', 2) is True
    assert owners.owners('key1') == [1, 2]
    assert owners.count('key1') == 2


def test_add_ignores_empty_keys_and_user_ids(owners):
    assert owners.add('', 1) is False
    assert owners.add('key1', 0) is False
    assert owners.is_empty() is True


def test_owned_keys_and_count_by_user(owners):
    owners.add('a', 1)
    owners.add('b', 1)
    owners.add('b', 2)
    assert owners.owned_keys(1) == {'a', 'b'}
    assert owners.owned_keys(2) == {'b'}
    assert owners.count_by_user() == {1: 2, 2: 1}


def test_remove_reports_the_owners_left(owners):
    owners.add('key1', 1)
    owners.add('key1', 2)
    assert owners.remove('key1', 1) == 1
    assert owners.owners('key1') == [2]
    assert owners.remove('key1', 2) == 0
    assert owners.count('key1') == 0


def test_drop_file_forgets_every_owner(owners):
    owners.add('key1', 1)
    owners.add('key1', 2)
    owners.drop_file('key1')
    assert owners.count('key1') == 0
    assert owners.is_empty() is True


def test_rekey_moves_rows_to_the_fresh_key(owners):
    owners.add('old', 1)
    assert owners.rekey('old', 'new', 'Artist/Track.mp3') == 1
    assert owners.owners('old') == []
    assert owners.owners('new') == [1]
    assert owners.rekey('', 'new') == 0
    assert owners.rekey('new', 'new') == 0


def test_rekey_drops_a_duplicate_the_user_already_owns(owners):
    owners.add('old', 1)
    # User 1 already owns the fresh key: the stale row must not survive
    # next to it.
    owners.add('new', 1)
    owners.rekey('old', 'new')
    assert owners.owners('old') == []
    assert owners.owners('new') == [1]


def test_add_heals_rows_left_at_the_same_path(owners):
    owners.add('stale', 1, 'Artist/Track.mp3')
    owners.add('fresh', 1, 'Artist/Track.mp3')
    assert owners.owners('stale') == []
    assert owners.owners('fresh') == [1]


def test_owned_subset_answers_only_for_that_user(owners):
    owners.add('a', 1, 'a.mp3')
    owners.add('b', 2, 'b.mp3')
    assert owners.owned_subset(['a', 'b', 'missing'], 1) == {'a'}
    assert owners.owned_subset([], 1) == set()
    assert owners.owned_subset(['a'], 0) == set()


def test_remove_user_drops_only_their_rows(owners):
    owners.add('a', 1)
    owners.add('a', 2)
    assert owners.remove_user(1) == 1
    assert owners.owners('a') == [2]
    assert owners.remove_user(99) == 0
