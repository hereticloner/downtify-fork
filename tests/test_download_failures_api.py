from __future__ import annotations

import asyncio

import pytest

from downtify import api
from downtify.download_failures import DownloadFailureStore


class _StubDownloader:
    def __init__(self):
        self.fail = True

    def download(self, song, progress_cb, subdir=None):
        if self.fail:
            raise RuntimeError(
                'network error https://example.test/path?token=secret-value'
            )
        return f'{song["song_id"]}.mp3'


def _prepare(monkeypatch, tmp_path):
    store = DownloadFailureStore(tmp_path / 'library.db')
    downloader = _StubDownloader()
    monkeypatch.setattr(api.state, 'download_failures', store, raising=False)
    monkeypatch.setattr(api.state, 'downloader', downloader)
    monkeypatch.setattr(api.state, 'download_semaphore', None)
    monkeypatch.setattr(api.state, 'pending_downloads', None)
    monkeypatch.setitem(api.state.download_jobs, 'abc', {'status': 'queued'})

    async def fake_broadcast(_message):
        return None

    monkeypatch.setattr(api.state.connections, 'broadcast', fake_broadcast)
    return store, downloader


def test_failed_download_is_recorded_and_successful_retry_resolves_it(
    monkeypatch, tmp_path
):
    store, downloader = _prepare(monkeypatch, tmp_path)
    song = {'song_id': 'abc', 'name': 'One', 'artist': 'A'}

    with pytest.raises(RuntimeError, match='network error'):
        asyncio.run(api._run_download(song, 'abc'))

    rows = store.list()
    assert len(rows) == 1
    assert rows[0]['code'] == 'download_failed'
    assert rows[0]['attempts'] == 1
    assert 'secret-value' not in rows[0]['message']
    assert 'https://' not in rows[0]['message']

    downloader.fail = False
    asyncio.run(api._run_download(song, 'abc'))

    assert store.list() == []
