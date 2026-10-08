"""Download queue maintenance endpoints."""

from __future__ import annotations

import asyncio

from downtify import api


def test_clear_completed_queue_removes_only_done_jobs():
    api.state.download_jobs.clear()
    try:
        done_id = api._register_job(
            {'song_id': 'done-1', 'name': 'A'}, status='done'
        )
        err_id = api._register_job(
            {'song_id': 'err-1', 'name': 'B'}, status='error'
        )
        q_id = api._register_job(
            {'song_id': 'q-1', 'name': 'C'}, status='queued'
        )

        result = api.clear_completed_queue()

        assert result['removed'] == 1
        assert done_id not in api.state.download_jobs
        assert err_id in api.state.download_jobs
        assert q_id in api.state.download_jobs
    finally:
        api.state.download_jobs.clear()


def test_clear_queue_removes_every_job():
    api.state.download_jobs.clear()
    try:
        api._register_job({'song_id': 'a-1', 'name': 'A'}, status='queued')
        api._register_job({'song_id': 'b-1', 'name': 'B'}, status='done')

        result = api.clear_queue()

        assert result == {'cleared': True}
        assert api.state.download_jobs == {}
    finally:
        api.state.download_jobs.clear()


def test_a_cleared_download_is_skipped_not_resurrected(monkeypatch):
    """Clear queue must stop pending downloads, not refill the list.

    ``_run_download`` used to re-register a job it couldn't find - a
    batch still churning after Clear queue re-added its songs to the
    queue one by one. A missing job now skips the download entirely:
    nothing re-registered, nothing broadcast.
    """

    broadcasts = []

    class FakeConnections:
        @staticmethod
        async def broadcast(payload):
            broadcasts.append(payload)

    monkeypatch.setattr(api.state, 'downloader', object())
    monkeypatch.setattr(api.state, 'connections', FakeConnections())
    jobs = {}
    monkeypatch.setattr(api.state, 'download_jobs', jobs)
    monkeypatch.setattr(api.state, 'download_paused', False)

    filename = asyncio.run(
        api._run_download({'song_id': 's-1', 'name': 'Song'}, 'gone')
    )

    assert filename is None
    assert jobs == {}
    assert broadcasts == []
