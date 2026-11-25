"""Tests for the per-playlist sub-folder support in ``Downloader``.

The download path itself is integration-heavy (yt-dlp + ffmpeg), so we
exercise the routing helpers in isolation: ``_resolve_target_dir`` and
``existing_filename_for``.
"""

from __future__ import annotations

from pathlib import Path

from downtify import downloader as downloader_mod
from downtify import lyrics as lyrics_mod
from downtify.downloader import Downloader


def test_metadata_lookup_forwards_synced_only(tmp_path, monkeypatch):
    seen = []

    def fetch(song, providers, cache, *, synced_only=False):
        seen.append(synced_only)
        return lyrics_mod.Lyrics(synced='[00:01.00]words')

    monkeypatch.setattr(lyrics_mod, 'fetch', fetch)
    downloader = Downloader(
        tmp_path,
        lyrics_providers=['lrclib'],
        lyrics_synced_only=True,
        download_cover_art=False,
    )
    song = {'name': 'Song', 'artists': ['Artist'], 'genre': 'Rock'}
    lookups = downloader_mod._MetadataLookups(downloader, song)
    try:
        assert lookups._lyrics.result(timeout=1).synced == '[00:01.00]words'
    finally:
        lookups.cancel()
    assert seen == [True]


def _make_downloader(tmp_path: Path) -> Downloader:
    return Downloader(tmp_path)


def test_resolve_target_dir_without_subdir_returns_download_dir(tmp_path):
    d = _make_downloader(tmp_path)
    target, prefix = d._resolve_target_dir(None)
    assert target == tmp_path
    assert not prefix


def test_resolve_target_dir_with_subdir_appends_sanitized_name(tmp_path):
    d = _make_downloader(tmp_path)
    target, prefix = d._resolve_target_dir('My Mix')
    assert target == tmp_path / 'My Mix'
    assert prefix == 'My Mix/'


def test_resolve_target_dir_sanitizes_unsafe_subdir(tmp_path):
    # '/' now separates nested path components; other unsafe characters are
    # stripped per-component.
    d = _make_downloader(tmp_path)
    target, prefix = d._resolve_target_dir('Bad/Name:Here?')
    assert target == tmp_path / 'Bad' / 'NameHere'
    assert prefix == 'Bad/NameHere/'


def test_resolve_target_dir_nests_multi_component_subdir(tmp_path):
    d = _make_downloader(tmp_path)
    target, prefix = d._resolve_target_dir('Sólrún/Auroric')
    assert target == tmp_path / 'Sólrún' / 'Auroric'
    assert prefix == 'Sólrún/Auroric/'


def test_existing_filename_finds_file_in_root(tmp_path):
    d = _make_downloader(tmp_path)
    (tmp_path / 'Artist - Song.mp3').write_bytes(b'\x00')
    name = d.existing_filename_for({'name': 'Song', 'artists': ['Artist']})
    assert name == 'Artist - Song.mp3'


def test_existing_filename_returns_none_when_missing(tmp_path):
    d = _make_downloader(tmp_path)
    assert (
        d.existing_filename_for({'name': 'Song', 'artists': ['Artist']})
        is None
    )


def test_existing_filename_with_subdir_returns_relative_path(tmp_path):
    d = _make_downloader(tmp_path)
    pl_dir = tmp_path / 'My Mix'
    pl_dir.mkdir()
    (pl_dir / 'Artist - Song.mp3').write_bytes(b'\x00')
    name = d.existing_filename_for(
        {'name': 'Song', 'artists': ['Artist']}, subdir='My Mix'
    )
    assert name == 'My Mix/Artist - Song.mp3'


def test_existing_filename_with_subdir_does_not_find_root_file(tmp_path):
    # File exists in the root but the lookup is scoped to a subdir,
    # so the root file must not match.
    d = _make_downloader(tmp_path)
    (tmp_path / 'Artist - Song.mp3').write_bytes(b'\x00')
    assert (
        d.existing_filename_for(
            {'name': 'Song', 'artists': ['Artist']}, subdir='My Mix'
        )
        is None
    )


def test_existing_filename_falls_back_to_alternate_extension(tmp_path):
    # yt-dlp occasionally keeps the upstream container (opus/m4a) even
    # when the configured format is mp3, so existing_filename_for must
    # match by basename, not by exact extension.
    d = _make_downloader(tmp_path)
    pl_dir = tmp_path / 'Mix'
    pl_dir.mkdir()
    (pl_dir / 'Artist - Song.opus').write_bytes(b'\x00')
    name = d.existing_filename_for(
        {'name': 'Song', 'artists': ['Artist']}, subdir='Mix'
    )
    assert name == 'Mix/Artist - Song.opus'
