"""Audio provider order in Downloader.download(): YouTube Music and
plain YouTube, on top of main's tagging pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from downtify import downloader as downloader_mod
from downtify.downloader import Downloader, NoAudioMatchError
from tests.test_downloader_extended import _minimal_mp3

_SONG = {
    'name': 'Track',
    'artists': ['Artist'],
    'album_name': 'Album',
    'cover_url': 'https://example.com/cover.jpg',
    'duration': 200,
}


def _fake_youtube_dl(fetched: list[str]):
    class _YoutubeDL:
        def __init__(self, opts):
            self.opts = opts
            self.params = opts

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def add_post_processor(self, pp, when='post_process'):
            pass

        def download(self, urls):
            fetched.extend(urls)
            _minimal_mp3(Path(self.opts['outtmpl'].replace('%(ext)s', 'mp3')))

    return _YoutubeDL


@pytest.fixture
def no_youtube(monkeypatch):
    fetched: list[str] = []
    monkeypatch.setattr(
        downloader_mod.yt_dlp, 'YoutubeDL', _fake_youtube_dl(fetched)
    )
    monkeypatch.setattr(
        downloader_mod.spotify_mod,
        'enrich_track_from_spotify_if_sparse',
        lambda song: song,
    )
    return fetched


def test_provider_label_reflects_youtube_fallback(
    tmp_path, monkeypatch, no_youtube
):
    # find_match returns no YouTube Music result when it fell back to
    # standard YouTube.
    monkeypatch.setattr(
        downloader_mod, 'find_match', lambda song: ('vid12345678', None)
    )
    reports = []
    d = Downloader(tmp_path)

    d.download(
        dict(_SONG),
        lambda pct, msg, provider=None: reports.append((msg, provider)),
    )

    assert reports[-1] == ('Done', 'youtube')


def test_youtube_only_provider(tmp_path, monkeypatch, no_youtube):
    def _boom(song):
        raise AssertionError('YouTube Music must not be searched')

    monkeypatch.setattr(downloader_mod, 'find_match', _boom)
    monkeypatch.setattr(
        downloader_mod, 'find_match_youtube_only', lambda song: 'vid12345678'
    )
    d = Downloader(tmp_path, audio_providers=['youtube'])

    assert d.download(dict(_SONG)) == 'Artist - Track.mp3'


def test_youtube_is_not_searched_again_after_youtube_music(
    tmp_path, monkeypatch, no_youtube
):
    calls = []

    def _youtube_only(song):
        calls.append(song)

    monkeypatch.setattr(
        downloader_mod, 'find_match', lambda song: (None, None)
    )
    monkeypatch.setattr(
        downloader_mod, 'find_match_youtube_only', _youtube_only
    )
    d = Downloader(tmp_path, audio_providers=['youtube-music', 'youtube'])

    with pytest.raises(NoAudioMatchError, match='a YouTube match'):
        d.download(dict(_SONG))
    # find_match already includes the standard-YouTube fallback.
    assert calls == []


def test_no_audio_match_reports_it_when_nothing_matches(
    tmp_path, monkeypatch, no_youtube
):
    monkeypatch.setattr(
        downloader_mod, 'find_match', lambda song: (None, None)
    )
    d = Downloader(tmp_path, audio_providers=['youtube-music'])

    with pytest.raises(RuntimeError, match='YouTube match'):
        d.download(dict(_SONG))


def test_audio_providers_are_normalized():
    assert Downloader._normalize_audio_providers(None) == ['youtube-music']
    # ``slskd`` is a leftover from the removed provider: dropped like any
    # other unknown name.
    assert Downloader._normalize_audio_providers([
        'slskd',
        'bogus',
        'slskd',
        'youtube',
    ]) == ['youtube']
