"""The monitor-history import runs once per monitor DB state.

``_open_library_stores`` used to re-scan the whole monitor history on every
start - one SQLite connection per row - which took minutes on a library of a
few hundred rows. The marker file records which monitor DB state was already
imported.
"""

from __future__ import annotations

import json

import main


def test_marker_roundtrip(tmp_path, monkeypatch):
    monitor_db = tmp_path / 'downtify_monitor.db'
    monitor_db.write_bytes(b'sqlite')
    monkeypatch.setattr(main, '_BACKFILL_MARKER', tmp_path / 'marker.json')

    assert main._backfill_done(monitor_db) is False
    main._mark_backfill_done(monitor_db)
    assert main._backfill_done(monitor_db) is True


def test_import_repeats_when_monitor_db_changes(tmp_path, monkeypatch):
    monitor_db = tmp_path / 'downtify_monitor.db'
    monitor_db.write_bytes(b'sqlite')
    monkeypatch.setattr(main, '_BACKFILL_MARKER', tmp_path / 'marker.json')
    main._mark_backfill_done(monitor_db)

    # A watch found tracks: the backfill has to look again.
    monitor_db.write_bytes(b'sqlite + new rows')
    assert main._backfill_done(monitor_db) is False


def test_missing_db_and_old_version_import_again(tmp_path, monkeypatch):
    marker = tmp_path / 'marker.json'
    monkeypatch.setattr(main, '_BACKFILL_MARKER', marker)
    monkeypatch.setattr(main, '_BACKFILL_VERSION', 2)
    assert main._backfill_done(tmp_path / 'missing.db') is False

    monitor_db = tmp_path / 'downtify_monitor.db'
    monitor_db.write_bytes(b'sqlite')
    marker.write_text(
        json.dumps({
            'version': 1,
            'monitor_db': main._backfill_signature(monitor_db),
        }),
        encoding='utf-8',
    )
    assert main._backfill_done(monitor_db) is False
