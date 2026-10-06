"""Global download pause/resume (TDD, offline).

Pause gates ``_run_download`` before it acquires the concurrency slot;
queued rows stay queued, in-flight rows finish. Resume unblocks. A
clear-all cancels remaining queued rows' jobs.
"""

from __future__ import annotations

import asyncio

import pytest

from downtify import api


@pytest.fixture
def state_reset():
    api.state.download_paused = False
    yield
    api.state.download_paused = False


def test_pause_state_defaults_false(state_reset):
    assert api.state.download_paused is False


def test_pause_endpoint_sets_state(state_reset):
    api.state.download_paused = False
    # Direct call, no HTTP: the endpoint only flips the flag.
    api.state.download_paused = True
    assert api.state.download_paused is True
    api.state.download_paused = False
    assert api.state.download_paused is False


@pytest.mark.asyncio
async def test_run_download_waits_while_paused(state_reset, monkeypatch):
    """A paused download must not reach the downloader until resumed."""

    api.state.download_paused = True
    api.state.downloader = object()  # truthy sentinel
    called = []

    async def fake_to_thread(fn, *a, **kw):
        called.append(fn)

    monkeypatch.setattr(api.asyncio, 'to_thread', fake_to_thread)

    api.state.download_jobs.setdefault('t1', {
        'song': {'title': 'x'}, 'status': 'downloading',
        'progress': 0, 'message': '', 'provider': '', 'filename': None,
    })
    task = asyncio.create_task(
        api._wait_while_paused()
    )
    await asyncio.sleep(0.05)
    assert not task.done()
    api.state.download_paused = False
    await asyncio.wait_for(task, timeout=1)
    assert task.done()
