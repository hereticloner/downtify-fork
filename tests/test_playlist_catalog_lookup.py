"""Tests for playlist catalog batch lookups and cleanup."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from downtify.library_cache_keys import file_content_key
from downtify.library_catalog import LibraryContext, list_library_entries
from downtify.library_metadata_cache import LibraryMetadataCache
from downtify.library_paths import locate_library_file
from downtify.library_reconcile import prune_stale_and_backfill
from downtify.playlist_catalog import PlaylistCatalog, _stored_content_key


def test_playlists_on_list_entries(tmp_path: Path) -> None:
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    track = download_dir / 'Artist - Song.mp3'
    track.write_bytes(b'audio-data-here')

    db = tmp_path / 'library.db'
    catalog = PlaylistCatalog(db)
    catalog.replace_playlist_tracks(
        'Road Mix',
        [({'song_id': '4uLU6hMCjMI75M1A2tKUQC'}, 'Artist - Song.mp3', track)],
    )

    cache = LibraryMetadataCache(db)
    cache.refresh('Artist - Song.mp3', track)
    ctx = LibraryContext(
        download_dir=download_dir,
        metadata_cache=cache,
        playlist_catalog=catalog,
    )
    entries = list_library_entries(ctx)
    assert len(entries) == 1
    assert entries[0]['playlists'] == ['Road Mix']


def test_backfill_from_monitor_db(tmp_path: Path) -> None:
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    track = download_dir / 'Artist - Song.mp3'
    track.write_bytes(b'audio')

    monitor_db = tmp_path / 'monitor.db'
    with sqlite3.connect(monitor_db) as conn:
        conn.executescript("""
            CREATE TABLE monitored_playlists (
                id INTEGER PRIMARY KEY,
                spotify_id TEXT NOT NULL,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                interval_minutes INTEGER DEFAULT 60,
                enabled INTEGER DEFAULT 1,
                last_checked TEXT,
                last_track_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE downloaded_tracks (
                id INTEGER PRIMARY KEY,
                playlist_id INTEGER NOT NULL,
                track_spotify_id TEXT NOT NULL,
                downloaded_at TEXT NOT NULL,
                filename TEXT
            );
            INSERT INTO monitored_playlists VALUES (
                1, 'playlist12345678901234567890', 'Old Mix', 'http://x', 60, 1, NULL, 0, 'now'
            );
            INSERT INTO downloaded_tracks VALUES (
                1, 1, '4uLU6hMCjMI75M1A2tKUQC', 'now', 'Artist - Song.mp3'
            );
        """)

    catalog = PlaylistCatalog(tmp_path / 'library.db')
    count = catalog.backfill_from_monitor_db(
        monitor_db, download_dir=download_dir
    )
    assert count == 1
    assert catalog.list_tracks('Old Mix')[0]['filename'] == 'Artist - Song.mp3'


def test_prune_stale_playlist_row(tmp_path: Path) -> None:
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    db = tmp_path / 'library.db'
    catalog = PlaylistCatalog(db)
    song = {'song_id': '4uLU6hMCjMI75M1A2tKUQC'}
    missing = download_dir / 'gone.mp3'
    catalog.upsert_track('My List', song, 'gone.mp3', missing)

    ctx = LibraryContext(download_dir=download_dir)
    pruned, _backfilled, affected = prune_stale_and_backfill(
        ctx, playlist_catalog=catalog
    )
    assert pruned == 1
    assert 'My List' in affected
    assert catalog.list_tracks('My List') == []


def test_backfill_from_monitor_db_twice_keeps_one_row(tmp_path: Path) -> None:
    """The import is batched (one connection, one transaction) and idempotent."""

    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    track = download_dir / 'Artist - Song.mp3'
    track.write_bytes(b'audio')

    monitor_db = tmp_path / 'monitor.db'
    with sqlite3.connect(monitor_db) as conn:
        conn.executescript("""
            CREATE TABLE monitored_playlists (
                id INTEGER PRIMARY KEY,
                spotify_id TEXT NOT NULL,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                interval_minutes INTEGER DEFAULT 60,
                enabled INTEGER DEFAULT 1,
                last_checked TEXT,
                last_track_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE downloaded_tracks (
                id INTEGER PRIMARY KEY,
                playlist_id INTEGER NOT NULL,
                track_spotify_id TEXT NOT NULL,
                downloaded_at TEXT NOT NULL,
                filename TEXT
            );
            INSERT INTO monitored_playlists VALUES (
                1, 'playlist12345678901234567890', 'Old Mix', 'http://x', 60, 1,
                NULL, 0, 'now'
            );
            INSERT INTO downloaded_tracks VALUES (
                1, 1, '4uLU6hMCjMI75M1A2tKUQC', 'now', 'Artist - Song.mp3'
            );
            INSERT INTO downloaded_tracks VALUES (
                2, 1, '0VjIjW4GlUZAMYd2vXMi3b', 'now', 'Artist - Gone.mp3'
            );
        """)

    catalog = PlaylistCatalog(tmp_path / 'library.db')
    assert (
        catalog.backfill_from_monitor_db(monitor_db, download_dir=download_dir)
        == 1
    )
    # Same history again: no duplicate rows, and the missing file stays out.
    assert (
        catalog.backfill_from_monitor_db(monitor_db, download_dir=download_dir)
        == 1
    )
    rows = catalog.list_tracks('Old Mix')
    assert [row['filename'] for row in rows] == ['Artist - Song.mp3']


def test_backfill_from_monitor_db_skips_ids_that_are_not_spotify(
    tmp_path: Path,
) -> None:
    """``upsert_track`` used to drop them, so the batched insert must too."""

    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    for name in ('Artist - Song.mp3', 'Artist - Youtube.mp3'):
        (download_dir / name).write_bytes(b'audio')

    monitor_db = tmp_path / 'monitor.db'
    with sqlite3.connect(monitor_db) as conn:
        conn.executescript("""
            CREATE TABLE monitored_playlists (
                id INTEGER PRIMARY KEY,
                spotify_id TEXT NOT NULL,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                interval_minutes INTEGER DEFAULT 60,
                enabled INTEGER DEFAULT 1,
                last_checked TEXT,
                last_track_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE downloaded_tracks (
                id INTEGER PRIMARY KEY,
                playlist_id INTEGER NOT NULL,
                track_spotify_id TEXT NOT NULL,
                downloaded_at TEXT NOT NULL,
                filename TEXT
            );
            INSERT INTO monitored_playlists VALUES (
                1, 'playlist12345678901234567890', 'Old Mix', 'http://x', 60, 1,
                NULL, 0, 'now'
            );
            INSERT INTO downloaded_tracks VALUES (
                1, 1, '4uLU6hMCjMI75M1A2tKUQC', 'now', 'Artist - Song.mp3'
            );
            INSERT INTO downloaded_tracks VALUES (
                2, 1, 'dQw4w9WgXcQ', 'now', 'Artist - Youtube.mp3'
            );
        """)

    catalog = PlaylistCatalog(tmp_path / 'library.db')
    linked = catalog.backfill_from_monitor_db(
        monitor_db, download_dir=download_dir
    )
    assert linked == 1
    rows = catalog.list_tracks('Old Mix')
    assert [row['filename'] for row in rows] == ['Artist - Song.mp3']


@pytest.mark.parametrize(
    'stored',
    [
        'Artist - Song.mp3',
        'Artist/Album/Artist - Song.mp3',
        'slskd/Artist - Soul.mp3',
        'slskd/Nested/Artist - Soul.mp3',
        'ext/deadbeef1234/Artist - External.mp3',
        'Artist - Gone.mp3',
        'Artist',
        '/absolute/Artist - Song.mp3',
        'not-a-library-key',
    ],
)
def test_stored_content_key_is_the_library_content_key(
    tmp_path: Path, stored: str
) -> None:
    """The startup import must write the key every other store joins on.

    ``library_catalog`` matches catalog rows to library files on the
    ``sha256(basename:size)`` key, so the import's cheaper lookup has to
    produce exactly what ``file_content_key`` produces.
    """

    download_dir = tmp_path / 'downloads'
    (download_dir / 'Artist' / 'Album').mkdir(parents=True)
    (download_dir / 'Artist').mkdir(exist_ok=True)
    (download_dir / 'Artist - Song.mp3').write_bytes(b'audio')
    (download_dir / 'Artist' / 'Album' / 'Artist - Song.mp3').write_bytes(
        b'other-audio'
    )
    slskd_dir = tmp_path / 'slskd'
    (slskd_dir / 'Nested').mkdir(parents=True)
    (slskd_dir / 'Artist - Soul.mp3').write_bytes(b'soul')
    (slskd_dir / 'Nested' / 'Artist - Soul.mp3').write_bytes(b'soul-nested')
    extra = tmp_path / 'extra'
    extra.mkdir()
    (extra / 'Artist - External.mp3').write_bytes(b'external')

    full = locate_library_file(stored, download_dir, slskd_dir, [extra])
    expected = None if full is None else file_content_key(full)
    assert _stored_content_key(stored, download_dir, slskd_dir) == expected


def test_stored_content_key_ignores_a_folder(tmp_path: Path) -> None:
    """A stored name pointing at a directory has no content key."""

    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    (download_dir / 'Artist').mkdir()
    assert _stored_content_key('Artist', download_dir, None) is None


def test_backfill_looks_up_each_file_name_once(
    tmp_path: Path, monkeypatch
) -> None:
    """One stat per distinct name, however many playlists hold it.

    The same file sits in every playlist that has it, and each lookup is a
    handful of syscalls on the library volume - which is what made the
    startup import slow.
    """

    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    (download_dir / 'Artist - Song.mp3').write_bytes(b'audio')

    monitor_db = tmp_path / 'monitor.db'
    with sqlite3.connect(monitor_db) as conn:
        conn.executescript("""
            CREATE TABLE monitored_playlists (
                id INTEGER PRIMARY KEY, spotify_id TEXT NOT NULL,
                name TEXT NOT NULL, url TEXT NOT NULL,
                interval_minutes INTEGER DEFAULT 60,
                enabled INTEGER DEFAULT 1, last_checked TEXT,
                last_track_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL);
            CREATE TABLE downloaded_tracks (
                id INTEGER PRIMARY KEY, playlist_id INTEGER NOT NULL,
                track_spotify_id TEXT NOT NULL,
                downloaded_at TEXT NOT NULL, filename TEXT);
        """)
        conn.executemany(
            'INSERT INTO monitored_playlists VALUES (?,?,?,?,60,1,NULL,0,?)',
            [
                (index, f'{index:022d}', f'Mix {index}', 'http://x', 'now')
                for index in (1, 2, 3)
            ],
        )
        conn.executemany(
            'INSERT INTO downloaded_tracks VALUES (?,?,?,?,?)',
            [
                (
                    index + 1,
                    index + 1,
                    '4uLU6hMCjMI75M1A2tKUQC',
                    'now',
                    'Artist - Song.mp3',
                )
                for index in range(3)
            ],
        )

    calls: list[str] = []
    real_locate = locate_library_file

    def counting_locate(stored, *args, **kwargs):
        calls.append(stored)
        return real_locate(stored, *args, **kwargs)

    monkeypatch.setattr(
        'downtify.playlist_catalog.locate_library_file', counting_locate
    )
    catalog = PlaylistCatalog(tmp_path / 'library.db')
    assert (
        catalog.backfill_from_monitor_db(monitor_db, download_dir=download_dir)
        == 3
    )

    # Three playlists, one file: the slow search runs at most once.
    assert calls.count('Artist - Song.mp3') <= 1
    assert len(catalog.list_tracks('Mix 1')) == 1
