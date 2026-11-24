from __future__ import annotations

import asyncio
import sqlite3

from downtify import api
from downtify.download_queue import PendingDownload, PendingDownloads


def _row(song_id: str, priority: str = 'normal') -> PendingDownload:
    return PendingDownload(
        song_id=song_id,
        song={'song_id': song_id, 'name': song_id},
        priority=priority,
    )


def test_existing_queue_rows_migrate_to_normal_priority(tmp_path):
    path = tmp_path / 'queue.db'
    with sqlite3.connect(path) as conn:
        conn.execute(
            'CREATE TABLE pending_downloads (seq INTEGER PRIMARY KEY '
            'AUTOINCREMENT, song_id TEXT NOT NULL UNIQUE, song TEXT NOT '
            "NULL, options TEXT NOT NULL DEFAULT '{}', user_ids TEXT NOT "
            "NULL DEFAULT '[]')"
        )
        conn.execute(
            'INSERT INTO pending_downloads (song_id, song) VALUES (?, ?)',
            ('one', '{"name":"one"}'),
        )

    store = PendingDownloads(path)

    assert store.rows()[0].priority == 'normal'
    with sqlite3.connect(path) as conn:
        columns = {
            row[1]
            for row in conn.execute('PRAGMA table_info(pending_downloads)')
        }
    assert 'priority' in columns


def test_restore_queue_filters_ids_and_does_not_duplicate_running_jobs(
    tmp_path, monkeypatch
):
    store = PendingDownloads(tmp_path / 'queue.db')
    store.add([
        PendingDownload('one', {'song_id': 'one', 'name': 'One'}),
        PendingDownload('two', {'song_id': 'two', 'name': 'Two'}),
    ])
    monkeypatch.setattr(api.state, 'pending_downloads', store)
    monkeypatch.setattr(api.state, 'downloader', object())
    monkeypatch.setitem(
        api.state.download_jobs, 'one', {'song': {'name': 'One'}}
    )
    captured = []

    async def fake_run(rows):
        captured.extend(row.song_id for row in rows)

    monkeypatch.setattr(api, '_run_restored_queue', fake_run)

    async def scenario():
        count = await api.restore_download_queue(['two'])
        await asyncio.sleep(0)
        return count

    assert asyncio.run(scenario()) == 1
    assert captured == ['two']
    assert 'two' in api.state.download_jobs


def test_rows_sort_high_before_normal_and_keep_fifo(tmp_path):
    store = PendingDownloads(tmp_path / 'queue.db')
    store.add([
        _row('normal-1'),
        _row('high-1', 'high'),
        _row('normal-2'),
        _row('high-2', 'high'),
    ])

    assert [row.song_id for row in store.rows()] == [
        'high-1',
        'high-2',
        'normal-1',
        'normal-2',
    ]


def test_set_priorities_updates_only_requested_rows(tmp_path):
    store = PendingDownloads(tmp_path / 'queue.db')
    store.add([_row('one'), _row('two')])

    changed = store.set_priorities(['one', 'missing'], 'high')

    assert changed == 1
    assert {row.song_id: row.priority for row in store.rows()} == {
        'one': 'high',
        'two': 'normal',
    }


def test_existing_job_keeps_its_priority_when_added_again(tmp_path):
    store = PendingDownloads(tmp_path / 'queue.db')
    store.add([_row('one', 'high')])
    store.add([_row('one', 'normal')])

    assert store.rows()[0].priority == 'high'


def test_invalid_priority_is_rejected(tmp_path):
    store = PendingDownloads(tmp_path / 'queue.db')
    store.add([_row('one')])

    try:
        store.set_priorities(['one'], 'urgent')
    except ValueError:
        pass
    else:
        raise AssertionError('invalid priority was accepted')
    assert store.rows()[0].priority == 'normal'
