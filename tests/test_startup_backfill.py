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


def test_marker_roundtrip(tmp_path, monkeypatch):
    monitor_db = _monitor_db(tmp_path / 'downtify_monitor.db')
    monkeypatch.setattr(main, '_BACKFILL_MARKER', tmp_path / 'marker.json')

    assert main._backfill_done(monitor_db) is False
    main._mark_backfill_done(monitor_db)
    assert main._backfill_done(monitor_db) is True


def test_import_repeats_when_tracks_arrive(tmp_path, monkeypatch):
    monitor_db = _monitor_db(tmp_path / 'downtify_monitor.db')
    monkeypatch.setattr(main, '_BACKFILL_MARKER', tmp_path / 'marker.json')
    main._mark_backfill_done(monitor_db)

    # A watch found a new track: the import has to look again.
    with sqlite3.connect(monitor_db) as conn:
        conn.execute(
            "INSERT INTO downloaded_tracks VALUES (?, 1, ?, 'now', ?)",
            (2, '0VjIjW4GlUZAMYd2vXMi3b', 'Artist - New.mp3'),
        )
    assert main._backfill_done(monitor_db) is False


def test_import_repeats_when_a_file_name_is_fixed(tmp_path, monkeypatch):
    monitor_db = _monitor_db(tmp_path / 'downtify_monitor.db')
    monkeypatch.setattr(main, '_BACKFILL_MARKER', tmp_path / 'marker.json')
    main._mark_backfill_done(monitor_db)

    with sqlite3.connect(monitor_db) as conn:
        conn.execute(
            'UPDATE downloaded_tracks SET filename = ? WHERE id = 1',
            ('Artist - Renamed.mp3',),
        )
    assert main._backfill_done(monitor_db) is False


def test_missing_db_and_old_version_import_again(tmp_path, monkeypatch):
    marker = tmp_path / 'marker.json'
    monkeypatch.setattr(main, '_BACKFILL_MARKER', marker)
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
