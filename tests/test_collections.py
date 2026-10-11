"""Failing tests first: playlist Collections (groups of playlists).

A collection is an ordered list of playlist names. Stored as one M3U
marker file per collection under ``Playlists/.collections/`` so it rides
the existing library scan (no new sqlite table, no migration).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from downtify.collection_rules import RuleError
from downtify.collections import (
    CollectionError,
    add_to_collection,
    create_collection,
    delete_collection,
    get_collection,
    list_collections,
    remove_from_collection,
    rename_collection,
    set_rules,
)


@pytest.fixture
def downloads(tmp_path: Path) -> Path:
    d = tmp_path / 'downloads'
    (d / 'Playlists' / '.collections').mkdir(parents=True)
    return d


def test_create_collection(downloads: Path) -> None:
    result = create_collection(downloads, 'Sabah Listesi')
    assert result['name'] == 'Sabah Listesi'
    assert list_collections(downloads) == [
        {'version': 1, 'name': 'Sabah Listesi', 'playlists': []}
    ]


def test_duplicate_collection_rejected(downloads: Path) -> None:
    create_collection(downloads, 'Sabah')
    with pytest.raises(CollectionError) as exc:
        create_collection(downloads, 'Sabah')
    assert exc.value.status_code == 409


def test_add_and_remove_playlists(downloads: Path) -> None:
    (downloads / 'Rock.m3u').write_text('#EXTM3U\n', encoding='utf-8')
    (downloads / 'Pop.m3u').write_text('#EXTM3U\n', encoding='utf-8')
    create_collection(downloads, 'Sabah')
    add_to_collection(downloads, 'Sabah', ['Rock', 'Pop'])
    assert list_collections(downloads)[0]['playlists'] == ['Rock', 'Pop']
    remove_from_collection(downloads, 'Sabah', ['Pop'])
    assert list_collections(downloads)[0]['playlists'] == ['Rock']


def test_unknown_playlist_rejected(downloads: Path) -> None:
    create_collection(downloads, 'Sabah')
    with pytest.raises(CollectionError) as exc:
        add_to_collection(downloads, 'Sabah', ['Yok Boyle Biri'])
    assert 'not a playlist' in str(exc.value)


def test_rename_collection(downloads: Path) -> None:
    create_collection(downloads, 'Eski')
    rename_collection(downloads, 'Eski', 'Yeni')
    names = [c['name'] for c in list_collections(downloads)]
    assert 'Yeni' in names
    assert 'Eski' not in names


def test_delete_collection(downloads: Path) -> None:
    create_collection(downloads, 'Gecici')
    delete_collection(downloads, 'Gecici')
    assert list_collections(downloads) == []


def test_storage_format_is_marker_json(downloads: Path) -> None:
    create_collection(downloads, 'Format')
    marker = downloads / 'Playlists' / '.collections' / 'Format.json'
    data = json.loads(marker.read_text(encoding='utf-8'))
    assert data['name'] == 'Format'
    assert data['playlists'] == []
    assert data.get('version') == 1


# ── Smart rules (backward compatible) ───────────────────────────────


def test_static_collection_list_output_is_unchanged(downloads: Path) -> None:
    create_collection(downloads, 'Plain')
    assert list_collections(downloads) == [
        {'version': 1, 'name': 'Plain', 'playlists': []}
    ]


def test_set_rules_persists_the_rule_list(downloads: Path) -> None:
    create_collection(downloads, 'Smart')
    set_rules(downloads, 'Smart', [{'type': 'genre', 'value': 'Rock'}])
    listed = list_collections(downloads)
    assert listed == [
        {
            'version': 1,
            'name': 'Smart',
            'playlists': [],
            'rules': [{'type': 'genre', 'value': 'Rock'}],
        }
    ]


def test_set_rules_normalizes_before_storing(downloads: Path) -> None:
    create_collection(downloads, 'Smart')
    set_rules(downloads, 'Smart', [{'type': 'plays', 'min': '2'}])
    marker = downloads / 'Playlists' / '.collections' / 'Smart.json'
    data = json.loads(marker.read_text(encoding='utf-8'))
    assert data['rules'] == [{'type': 'plays', 'min': 2, 'max': None}]


def test_set_rules_rejects_an_invalid_rule(downloads: Path) -> None:
    create_collection(downloads, 'Smart')
    with pytest.raises(RuleError) as exc:
        set_rules(downloads, 'Smart', [{'type': 'bpm', 'value': 120}])
    assert exc.value.status_code == 400


def test_set_rules_clears_with_an_empty_list(downloads: Path) -> None:
    create_collection(downloads, 'Smart')
    set_rules(downloads, 'Smart', [{'type': 'genre', 'value': 'Rock'}])
    set_rules(downloads, 'Smart', [])
    # Back to the static shape: no rules key, nothing computed.
    assert list_collections(downloads) == [
        {'version': 1, 'name': 'Smart', 'playlists': []}
    ]


def test_get_collection_returns_the_stored_document(downloads: Path) -> None:
    create_collection(downloads, 'Smart')
    set_rules(downloads, 'Smart', [{'type': 'genre', 'value': 'Rock'}])
    got = get_collection(downloads, 'Smart')
    assert got['name'] == 'Smart'
    assert got['rules'] == [{'type': 'genre', 'value': 'Rock'}]
    with pytest.raises(CollectionError) as exc:
        get_collection(downloads, 'Yok')
    assert exc.value.status_code == 404


def test_rename_keeps_the_rules(downloads: Path) -> None:
    create_collection(downloads, 'Smart')
    set_rules(downloads, 'Smart', [{'type': 'genre', 'value': 'Rock'}])
    rename_collection(downloads, 'Smart', 'Smarter')
    listed = list_collections(downloads)
    assert listed == [
        {
            'version': 1,
            'name': 'Smarter',
            'playlists': [],
            'rules': [{'type': 'genre', 'value': 'Rock'}],
        }
    ]


def test_hand_written_broken_rules_do_not_crash_the_listing(
    downloads: Path,
) -> None:
    create_collection(downloads, 'Smart')
    marker = downloads / 'Playlists' / '.collections' / 'Smart.json'
    raw = json.loads(marker.read_text(encoding='utf-8'))
    raw['rules'] = [{'type': 'bpm', 'value': 120}]
    marker.write_text(json.dumps(raw), encoding='utf-8')
    # Unknown rules saved by hand are skipped at read time, not fatal.
    assert list_collections(downloads)[0].get('rules') is None
