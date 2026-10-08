"""The monitor DB must survive concurrent use.

A sweep writes one row per downloaded track while the Monitor page
reads the watch list; the check endpoint writes through the same
file. Connections therefore need WAL and a busy timeout — without
them a long sweep held the lock and both ``GET /api/monitor/playlists``
and the per-watch check answered 500s
(``sqlite3.OperationalError: database is locked``).
"""

from __future__ import annotations

import sqlite3

from downtify.monitor import PlaylistMonitorDB


def _db(tmp_path):
    return PlaylistMonitorDB(tmp_path / 'monitor.db')


def test_connections_use_wal_a_busy_timeout_and_foreign_keys(tmp_path):
    db = _db(tmp_path)
    with db._connect() as conn:
        mode = str(conn.execute('PRAGMA journal_mode').fetchone()[0])
        busy = int(conn.execute('PRAGMA busy_timeout').fetchone()[0])
        keys = int(conn.execute('PRAGMA foreign_keys').fetchone()[0])
    assert mode == 'wal'
    assert busy >= 30000
    assert keys == 1


def test_reads_survive_an_open_write_transaction(tmp_path):
    """A held write transaction must not make a page read fail."""

    db = _db(tmp_path)
    db.add_playlist(
        'fjWkr7Jh13WAWIyKaaUW06',
        'P1',
        'https://open.spotify.com/playlist/fjWkr7Jh13WAWIyKaaUW06',
    )

    held = sqlite3.connect(db._path)
    try:
        held.execute('BEGIN IMMEDIATE')
        rows = db.list_playlists()
        assert rows[0].spotify_id == 'fjWkr7Jh13WAWIyKaaUW06'
        assert rows[0].name == 'P1'
    finally:
        held.rollback()
        held.close()
