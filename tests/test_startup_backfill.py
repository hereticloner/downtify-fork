"""The monitor-history import runs once per monitor DB state.

``_open_library_stores`` used to re-scan the whole monitor history on every
start - one SQLite connection per row - which took minutes on a library of a
few hundred rows. The marker file records which history was already imported.

The monitor writes ``last_checked`` into its database on every check, so the
signature deliberately ignores timestamps: only the downloaded tracks matter.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

import main


def _monitor_db(path, filenames=('Artist - Song.mp3',)):
    with sqlite3.connect(path) as conn:
        conn.execute(
            """CREATE TABLE downloaded_tracks (
                   id INTEGER PRIMARY KEY,
                   playlist_id INTEGER NOT NULL,
                   track_spotify_id TEXT NOT NULL,
                   downloaded_at TEXT NOT NULL,
                   filename TEXT
               )"""
        )
        conn.executemany(
            'INSERT INTO downloaded_tracks VALUES (?, 1, ?, ?, ?)',
            [
                (index + 1, f'{index:022d}', 'now', filename)
                for index, filename in enumerate(filenames)
            ],
        )
    return path


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """``/data`` with the library file the import fills, and the marker in it."""

    data = tmp_path / 'data'
    data.mkdir()
    (data / 'downtify_library.db').write_bytes(b'')
    monkeypatch.setattr(main, 'DATABASE_DIR', data)
    monkeypatch.setattr(
        main, '_BACKFILL_MARKER', data / 'downtify_backfill.json'
    )
    return data


def test_marker_roundtrip(tmp_path, data_dir):
    monitor_db = _monitor_db(tmp_path / 'downtify_monitor.db')

    assert main._backfill_done(monitor_db) is False
    main._mark_backfill_done(monitor_db)
    assert main._backfill_done(monitor_db) is True


def test_import_repeats_when_tracks_arrive(tmp_path, data_dir):
    monitor_db = _monitor_db(tmp_path / 'downtify_monitor.db')
    main._mark_backfill_done(monitor_db)

    # A watch found a new track: the import has to look again.
    with sqlite3.connect(monitor_db) as conn:
        conn.execute(
            "INSERT INTO downloaded_tracks VALUES (?, 1, ?, 'now', ?)",
            (2, '0VjIjW4GlUZAMYd2vXMi3b', 'Artist - New.mp3'),
        )
    assert main._backfill_done(monitor_db) is False


def test_import_repeats_when_a_file_name_is_fixed(tmp_path, data_dir):
    monitor_db = _monitor_db(tmp_path / 'downtify_monitor.db')
    main._mark_backfill_done(monitor_db)

    with sqlite3.connect(monitor_db) as conn:
        conn.execute(
            'UPDATE downloaded_tracks SET filename = ? WHERE id = 1',
            ('Artist - Renamed.mp3',),
        )
    assert main._backfill_done(monitor_db) is False


def test_import_repeats_when_the_library_file_is_gone(tmp_path, data_dir):
    """A wiped /data must import again even though the marker survived."""

    monitor_db = _monitor_db(tmp_path / 'downtify_monitor.db')
    main._mark_backfill_done(monitor_db)
    assert main._backfill_done(monitor_db) is True

    (data_dir / 'downtify_library.db').unlink()
    assert main._backfill_done(monitor_db) is False


def test_missing_db_and_old_version_import_again(
    tmp_path, data_dir, monkeypatch
):
    marker = data_dir / 'downtify_backfill.json'
    monkeypatch.setattr(main, '_BACKFILL_VERSION', 2)
    assert main._backfill_done(tmp_path / 'missing.db') is False

    monitor_db = _monitor_db(tmp_path / 'downtify_monitor.db')
    marker.write_text(
        json.dumps({
            'version': 1,
            'monitor_db': main._backfill_signature(monitor_db),
        }),
        encoding='utf-8',
    )
    assert main._backfill_done(monitor_db) is False


def test_signature_of_a_file_that_is_not_a_database(tmp_path):
    broken = tmp_path / 'broken.db'
    broken.write_bytes(b'not sqlite')
    assert not main._backfill_signature(broken)


def test_an_unwritable_marker_does_not_break_the_import(
    tmp_path, data_dir, monkeypatch
):
    """Writing the marker is best effort: a read-only /data still imports."""

    monitor_db = _monitor_db(tmp_path / 'downtify_monitor.db')
    monkeypatch.setattr(
        main, '_BACKFILL_MARKER', tmp_path / 'missing-dir' / 'marker.json'
    )
    main._mark_backfill_done(monitor_db)  # must not raise
    assert main._backfill_done(monitor_db) is False


def _app(tmp_path, monkeypatch):
    """``build_app`` with /data, /downloads and the marker under *tmp_path*."""

    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html>Downtify</html>')
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', downloads)
    monkeypatch.setattr(main, 'DATABASE_DIR', tmp_path / 'data')
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))
    monkeypatch.setattr(
        main, '_BACKFILL_MARKER', tmp_path / 'data' / 'downtify_backfill.json'
    )
    main.build_app()
    return downloads


def test_open_library_stores_imports_once(tmp_path, monkeypatch):
    """The real startup function: one import, then nothing on the next start."""

    downloads = _app(tmp_path, monkeypatch)
    (downloads / 'Artist - Song.mp3').write_bytes(b'audio')
    monitor_db = _monitor_db(tmp_path / 'downtify_monitor.db')
    with sqlite3.connect(monitor_db) as conn:
        conn.execute(
            """CREATE TABLE monitored_playlists (
                   id INTEGER PRIMARY KEY,
                   spotify_id TEXT NOT NULL,
                   name TEXT NOT NULL,
                   url TEXT NOT NULL,
                   interval_minutes INTEGER DEFAULT 60,
                   enabled INTEGER DEFAULT 1,
                   last_checked TEXT,
                   last_track_count INTEGER DEFAULT 0,
                   created_at TEXT NOT NULL
               )"""
        )
        conn.execute(
            'INSERT INTO monitored_playlists VALUES '
            "(1, 'playlist0000000000000001', 'Old Mix', 'http://x', 60, 1, "
            "NULL, 0, 'now')"
        )

    imported = []
    original = main.TrackIndex.backfill_from_monitor_db

    def spy(self, path):
        imported.append(path)
        return original(self, path)

    monkeypatch.setattr(main.TrackIndex, 'backfill_from_monitor_db', spy)

    # The track index import is cheap and stays on the startup path; the
    # playlist catalog half is deferred (see the tests below).
    assert main._open_library_stores(monitor_db) is True
    assert len(imported) == 1
    assert main.api.state.playlist_catalog.list_tracks('Old Mix') == []

    main._backfill_library_history(monitor_db, catalog_import=True)
    assert main._backfill_done(monitor_db) is True
    assert main.api.state.playlist_catalog.list_tracks('Old Mix')

    # Same history on the next start: the import is skipped, not repeated.
    assert main._open_library_stores(monitor_db) is False
    assert len(imported) == 1


def test_the_playlist_catalog_import_does_not_block_startup(
    tmp_path, monkeypatch
):
    """Opening the stores must not stat a file per history row.

    Linking the playlist catalog walks every downloaded-track row and hits
    the library volume once per distinct file, which held up the first
    request for minutes on a large library. It now runs after startup.
    """

    downloads = _app(tmp_path, monkeypatch)
    for index in range(3):
        (downloads / f'Artist - Song {index}.mp3').write_bytes(b'audio')
    monitor_db = _monitor_db(
        tmp_path / 'downtify_monitor.db',
        filenames=tuple(f'Artist - Song {i}.mp3' for i in range(3)),
    )
    with sqlite3.connect(monitor_db) as conn:
        conn.execute(
            """CREATE TABLE monitored_playlists (
                   id INTEGER PRIMARY KEY,
                   spotify_id TEXT NOT NULL,
                   name TEXT NOT NULL,
                   url TEXT NOT NULL,
                   interval_minutes INTEGER DEFAULT 60,
                   enabled INTEGER DEFAULT 1,
                   last_checked TEXT,
                   last_track_count INTEGER DEFAULT 0,
                   created_at TEXT NOT NULL
               )"""
        )
        conn.execute(
            'INSERT INTO monitored_playlists VALUES '
            "(1, 'playlist0000000000000001', 'Old Mix', 'http://x', 60, 1, "
            "NULL, 0, 'now')"
        )

    def explode(*args, **kwargs):
        raise AssertionError('the catalog import ran on the startup path')

    catalog = main.api.state.playlist_catalog
    real_import = catalog.backfill_from_monitor_db
    monkeypatch.setattr(catalog, 'backfill_from_monitor_db', explode)
    assert main._open_library_stores(monitor_db) is True

    # The deferred half still imports once it is actually run.
    monkeypatch.setattr(catalog, 'backfill_from_monitor_db', real_import)
    main._backfill_library_history(monitor_db, catalog_import=True)
    assert len(main.api.state.playlist_catalog.list_tracks('Old Mix')) == 3


def test_the_deferred_import_registers_batch_rows(tmp_path, monkeypatch):
    """Batch rows are registered even when the history was already imported."""

    downloads = _app(tmp_path, monkeypatch)
    (downloads / 'Artist - Song.mp3').write_bytes(b'audio')
    monitor_db = _monitor_db(tmp_path / 'downtify_monitor.db')
    with sqlite3.connect(monitor_db) as conn:
        conn.execute(
            """CREATE TABLE monitored_playlists (
                   id INTEGER PRIMARY KEY,
                   spotify_id TEXT NOT NULL,
                   name TEXT NOT NULL,
                   url TEXT NOT NULL,
                   interval_minutes INTEGER DEFAULT 60,
                   enabled INTEGER DEFAULT 1,
                   last_checked TEXT,
                   last_track_count INTEGER DEFAULT 0,
                   created_at TEXT NOT NULL
               )"""
        )
        conn.execute(
            'INSERT INTO monitored_playlists VALUES '
            "(1, 'playlist0000000000000001', 'Old Mix', 'http://x', 60, 1, "
            "NULL, 0, 'now')"
        )

    assert main._open_library_stores(monitor_db) is True
    main._backfill_library_history(monitor_db, catalog_import=True)
    registered = [
        batch['spotify_playlist_id']
        for batch in main.api.state.playlist_batch_store.list_latest_batches()
    ]
    assert 'playlist0000000000000001' in registered


def test_the_deferred_import_marks_the_history_imported(tmp_path, monkeypatch):
    """A restart before the deferred half ran has to import again."""

    downloads = _app(tmp_path, monkeypatch)
    (downloads / 'Artist - Song.mp3').write_bytes(b'audio')
    monitor_db = _monitor_db(tmp_path / 'downtify_monitor.db')

    main._open_library_stores(monitor_db)
    assert main._backfill_done(monitor_db) is False

    main._backfill_library_history(monitor_db, catalog_import=True)
    assert main._backfill_done(monitor_db) is True
