from __future__ import annotations

from pathlib import Path

from mutagen.id3 import ID3, USLT

from downtify import lyrics_health
from downtify.library_catalog import LibraryContext, list_library_path_pairs
from downtify.track_index import TrackIndex


def _plain_mp3(path: Path, text: str) -> None:
    tags = ID3()
    tags.add(USLT(encoding=3, lang='eng', desc='', text=text))
    tags.save(str(path), v2_version=4)


def test_fill_rechecks_current_lyrics(tmp_path: Path, monkeypatch) -> None:
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    track = downloads / 'Song.mp3'
    track.write_bytes(b'x')
    monkeypatch.setattr(
        lyrics_health,
        'read_audio_metadata',
        lambda path: {'title': 'Song', 'artists': ['Artist'], 'duration': 1},
    )
    ctx = LibraryContext(download_dir=downloads)
    assert lyrics_health.scan_lyrics_health(ctx)['summary']['missing'] == 1
    track.with_suffix('.lrc').write_text(
        '[00:01.00]appeared later', encoding='utf-8'
    )

    def never(*_args, **_kwargs):
        raise AssertionError('already-synced track must not be fetched')

    monkeypatch.setattr(lyrics_health.lyrics_mod, 'fetch', never)
    result = lyrics_health.fill_lyrics(
        ['Song.mp3'],
        ctx,
        {'download_lyrics': True, 'lyrics_providers': ['lrclib']},
        None,
    )

    assert result['written'] == 0
    assert result['skipped'] == 1
    assert result['failed'] == 0


def test_fill_continues_after_one_failure(tmp_path: Path, monkeypatch) -> None:
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    for name in ('Bad.mp3', 'Good.mp3'):
        (downloads / name).write_bytes(b'x')
    monkeypatch.setattr(
        lyrics_health,
        'read_audio_metadata',
        lambda path: {
            'title': path.stem,
            'artists': ['Artist'],
            'duration': 1,
        },
    )

    def fetch(song, *_args, **_kwargs):
        if song['name'] == 'Bad':
            raise RuntimeError('provider failed')
        return lyrics_health.lyrics_mod.Lyrics(synced='[00:01.00]good')

    def write(path, found, *, sidecar=None):
        path.with_suffix('.lrc').write_text(found.synced, encoding='utf-8')

    monkeypatch.setattr(lyrics_health.lyrics_mod, 'fetch', fetch)
    monkeypatch.setattr(lyrics_health.lyrics_mod, 'write_to_file', write)

    result = lyrics_health.fill_lyrics(
        ['Bad.mp3', 'Good.mp3'],
        LibraryContext(download_dir=downloads),
        {'download_lyrics': True, 'lyrics_providers': ['lrclib']},
        None,
    )

    assert result['found'] == 1
    assert result['written'] == 1
    assert result['failed'] == 1
    assert result['errors'] == [{'file': 'Bad.mp3', 'code': 'lyrics_failed'}]


def test_fill_skips_already_synced_and_rejects_outside_paths(
    tmp_path: Path, monkeypatch
) -> None:
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    synced = downloads / 'Synced.mp3'
    missing = downloads / 'Missing.mp3'
    synced.write_bytes(b'x')
    missing.write_bytes(b'x')
    synced.with_suffix('.lrc').write_text(
        '[00:01.00]already', encoding='utf-8'
    )
    monkeypatch.setattr(
        lyrics_health,
        'read_audio_metadata',
        lambda path: {
            'title': path.stem,
            'artists': ['Artist'],
            'duration': 1,
        },
    )

    def fetch(*_args, **_kwargs):
        return lyrics_health.lyrics_mod.Lyrics(synced='[00:01.00]new')

    def write(path, found, *, sidecar=None):
        path.with_suffix('.lrc').write_text(found.synced, encoding='utf-8')

    monkeypatch.setattr(lyrics_health.lyrics_mod, 'fetch', fetch)
    monkeypatch.setattr(lyrics_health.lyrics_mod, 'write_to_file', write)
    result = lyrics_health.fill_lyrics(
        ['Synced.mp3', '../secret.mp3', 'Missing.mp3'],
        LibraryContext(download_dir=downloads),
        {'download_lyrics': True, 'lyrics_providers': ['lrclib']},
        None,
    )

    assert result['requested'] == 3
    assert result['found'] == 1
    assert result['written'] == 1
    assert result['skipped'] == 1
    assert result['failed'] == 1
    assert result['errors'] == [
        {'file': '../secret.mp3', 'code': 'invalid_path'}
    ]


def test_fill_writes_only_after_explicit_request(
    tmp_path: Path, monkeypatch
) -> None:
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    track = downloads / 'Song.mp3'
    track.write_bytes(b'x')
    monkeypatch.setattr(
        lyrics_health,
        'read_audio_metadata',
        lambda path: {
            'title': 'Song',
            'artists': ['Artist'],
            'duration': 1,
        },
    )
    fetched = []
    written = []

    def fetch(song, providers, cache, *, synced_only=False):
        fetched.append(song['name'])
        return lyrics_health.lyrics_mod.Lyrics(synced='[00:01.00]words')

    def write(path, found, *, sidecar=None):
        written.append(path.name)
        path.with_suffix('.lrc').write_text(found.synced, encoding='utf-8')

    monkeypatch.setattr(lyrics_health.lyrics_mod, 'fetch', fetch)
    monkeypatch.setattr(lyrics_health.lyrics_mod, 'write_to_file', write)
    ctx = LibraryContext(download_dir=downloads)
    lyrics_health.scan_lyrics_health(ctx)
    assert fetched == []

    class Cache:
        def __init__(self):
            self.forgotten = []

        def forget(self, key):
            self.forgotten.append(key)
            return 1

    cache = Cache()
    result = lyrics_health.fill_lyrics(
        ['Song.mp3'],
        ctx,
        {'download_lyrics': True, 'lyrics_providers': ['lrclib']},
        cache,
    )

    assert result == {
        'requested': 1,
        'found': 1,
        'written': 1,
        'skipped': 0,
        'failed': 0,
        'errors': [],
    }
    assert fetched == ['Song']
    assert written == ['Song.mp3']
    assert cache.forgotten == ['text:artist|song']


def test_scan_uses_fresh_disk_snapshot(tmp_path: Path, monkeypatch) -> None:
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    track = downloads / 'Song.mp3'
    track.write_bytes(b'x')
    monkeypatch.setattr(
        lyrics_health,
        'read_audio_metadata',
        lambda path: {'title': 'Song', 'artist': 'Artist', 'duration': 1},
    )
    ctx = LibraryContext(download_dir=downloads)
    assert list_library_path_pairs(ctx)
    track.unlink()

    report = lyrics_health.scan_lyrics_health(ctx)

    assert report['summary']['tracks'] == 0
    assert report['findings'] == []


def test_scan_is_read_only(tmp_path: Path, monkeypatch) -> None:
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    track = downloads / 'Song.mp3'
    track.write_bytes(b'audio')
    sidecar = track.with_suffix('.lrc')
    sidecar.write_text('[00:01.00]words', encoding='utf-8')
    index = TrackIndex(tmp_path / 'library.db')
    index.register('4uLU6hMCjMI75M1A2tKUQC', 'Song.mp3', full_path=track)
    monkeypatch.setattr(
        lyrics_health,
        'read_audio_metadata',
        lambda path: {'title': 'Song', 'artist': 'Artist', 'duration': 1},
    )
    ctx = LibraryContext(download_dir=downloads)
    before = (
        track.read_bytes(),
        sidecar.read_bytes(),
        index.all_rows(),
        sorted(
            path.relative_to(downloads)
            for path in downloads.rglob('*')
            if path.is_file()
        ),
    )

    lyrics_health.scan_lyrics_health(ctx, index)
    lyrics_health.scan_lyrics_health(ctx, index)

    assert track.read_bytes() == before[0]
    assert sidecar.read_bytes() == before[1]
    assert index.all_rows() == before[2]
    assert (
        sorted(
            path.relative_to(downloads)
            for path in downloads.rglob('*')
            if path.is_file()
        )
        == before[3]
    )


def test_scan_missing_root_is_partial(tmp_path: Path) -> None:
    report = lyrics_health.scan_lyrics_health(
        LibraryContext(download_dir=tmp_path / 'missing')
    )

    assert report['sources']['disk'] is False
    assert report['warnings'] == ['disk_unavailable']
    assert report['summary']['tracks'] == 0


def test_scan_classifies_synced_plain_and_missing(
    tmp_path: Path, monkeypatch
) -> None:
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    synced = downloads / 'Synced.mp3'
    plain = downloads / 'Plain.mp3'
    missing = downloads / 'Missing.mp3'
    synced.write_bytes(b'x')
    _plain_mp3(plain, 'plain words')
    missing.write_bytes(b'x')
    synced.with_suffix('.lrc').write_text(
        '[00:01.00]timed words', encoding='utf-8'
    )
    monkeypatch.setattr(
        lyrics_health,
        'read_audio_metadata',
        lambda path: {
            'title': path.stem,
            'artist': 'Artist',
            'album': 'Album',
            'duration': 123.0,
        },
    )

    report = lyrics_health.scan_lyrics_health(
        LibraryContext(download_dir=downloads)
    )

    assert report['summary'] == {
        'tracks': 3,
        'synced': 1,
        'plain_only': 1,
        'missing': 1,
    }
    assert {row['file']: row['status'] for row in report['findings']} == {
        'Synced.mp3': 'synced',
        'Plain.mp3': 'plain_only',
        'Missing.mp3': 'missing',
    }
