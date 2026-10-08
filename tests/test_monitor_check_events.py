"""``monitor_check`` lifecycle events for the web UI.

A manual "Check now" spawns the sweep in the background: the events
(``start``, per-track ``progress``, ``end``/``error``) are what the
Monitor page's progress bar feeds on. Tests capture the broadcast.
"""

from __future__ import annotations

import asyncio

import pytest

from downtify import monitor
from downtify.monitor import KIND_PLAYLIST, PlaylistMonitorDB

PLAYLIST_ID = 'fjWkr7Jh13WAWIyKaaUW06'
TRACKS = [
    {'song_id': 'A' * 22, 'name': 'Alpha', 'artists': ['Artist']},
    {'song_id': 'B' * 22, 'name': 'Beta', 'artists': ['Artist']},
]


class _Downloader:
    """Downloads by writing a file, like the sweep expects."""

    def __init__(self, download_dir) -> None:
        self.download_dir = download_dir
        self.downloaded = []

    def download(self, song, progress=None, subdir=None):
        self.downloaded.append(song['song_id'])
        name = f'{subdir}/{song["name"]}.mp3'
        path = self.download_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'audio')
        return name


class _Collector:
    """A broadcast that keeps only ``monitor_check`` events."""

    def __init__(self) -> None:
        self.events: list[dict] = []

    async def __call__(self, msg: dict) -> None:
        if msg.get('type') == 'monitor_check':
            self.events.append(msg)


def _fake_songs(monkeypatch):
    monkeypatch.setattr(
        monitor.spotify, 'playlist_tracks_from_id', lambda _id: TRACKS
    )
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda _id: {})


def _watch(tmp_path):
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    playlist = db.get_by_spotify_id(PLAYLIST_ID) or db.add_playlist(
        PLAYLIST_ID,
        'Road Trip',
        f'https://open.spotify.com/playlist/{PLAYLIST_ID}',
    )
    return db, playlist


def _run_in_loop(coro_factory):
    """Build and drive the coroutine on a fresh loop.

    The factory takes the loop: building the coroutine needs it before
    the loop starts running.
    """

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro_factory(loop))
    finally:
        loop.close()


def _sweep_playlist(db, playlist, broadcast, downloader, loop):
    return monitor.check_playlist(
        playlist,
        db,
        downloader,
        broadcast,
        loop,
        {'generate_m3u': False},
        None,
    )


def _watch_check(db, playlist, broadcast, downloader, loop):
    return monitor.check_watch(
        playlist,
        db,
        downloader,
        broadcast,
        loop,
        {'generate_m3u': False},
        None,
    )


def test_check_playlist_emits_per_track_progress(monkeypatch, tmp_path):
    _fake_songs(monkeypatch)
    collector = _Collector()
    db, playlist = _watch(tmp_path)
    downloader = _Downloader(tmp_path / 'downloads')

    count = _run_in_loop(
        lambda loop: _sweep_playlist(db, playlist, collector, downloader, loop)
    )

    assert count == 2
    assert [(e['phase'], e['done'], e['total']) for e in collector.events] == [
        ('progress', 1, 2),
        ('progress', 2, 2),
    ]
    assert {e['name'] for e in collector.events} == {'Road Trip'}
    assert collector.events[0]['id'] > 0


def test_check_playlist_is_silent_when_nothing_is_new(monkeypatch, tmp_path):
    _fake_songs(monkeypatch)
    db, playlist = _watch(tmp_path)
    downloader = _Downloader(tmp_path / 'downloads')
    _run_in_loop(
        lambda loop: _sweep_playlist(
            db, playlist, _Collector(), downloader, loop
        )
    )

    collector = _Collector()
    count = _run_in_loop(
        lambda loop: _sweep_playlist(db, playlist, collector, downloader, loop)
    )

    # Second sweep: both tracks were recorded the first time around.
    assert count == 0
    assert collector.events == []


def test_check_watch_brackets_the_sweep(monkeypatch, tmp_path):
    collector = _Collector()
    seen: list[dict] = []

    async def check(  # noqa: PLR0913, PLR0917
        playlist, db, downloader, broadcast, loop, settings=None, library=None
    ):
        assert broadcast is collector
        assert playlist.kind == KIND_PLAYLIST
        seen.append({'kind': playlist.kind, 'id': playlist.id})
        return 3

    _fake_songs(monkeypatch)
    monkeypatch.setattr(monitor, 'check_playlist', check)
    db, playlist = _watch(tmp_path)
    downloader = _Downloader(tmp_path / 'downloads')

    count = _run_in_loop(
        lambda loop: monitor.check_watch(
            playlist,
            db,
            downloader,
            collector,
            loop,
            {'generate_m3u': False},
            None,
        )
    )

    assert count == 3
    assert seen == [{'kind': KIND_PLAYLIST, 'id': playlist.id}]
    assert [e['phase'] for e in collector.events] == ['start', 'end']
    assert collector.events[0]['kind'] == KIND_PLAYLIST
    assert collector.events[-1]['downloaded'] == 3
    assert collector.events[0]['id'] == collector.events[-1]['id']


def test_check_watch_reports_an_error(monkeypatch, tmp_path):
    collector = _Collector()

    async def check(  # noqa: PLR0913, PLR0917
        playlist, db, downloader, broadcast, loop, settings=None, library=None
    ):
        raise RuntimeError('boom')

    _fake_songs(monkeypatch)
    monkeypatch.setattr(monitor, 'check_playlist', check)
    db, playlist = _watch(tmp_path)
    downloader = _Downloader(tmp_path / 'downloads')

    async def run(loop):
        await monitor.check_watch(
            playlist,
            db,
            downloader,
            collector,
            loop,
            {'generate_m3u': False},
            None,
        )

    with pytest.raises(RuntimeError, match='boom'):
        _run_in_loop(run)

    assert [e['phase'] for e in collector.events] == ['start', 'error']
