from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from downtify import library_health as health_mod
from downtify import monitor as monitor_mod
from downtify.library_catalog import LibraryContext
from downtify.library_health import scan_library_health
from downtify.navidrome_index import NavidromeIndex
from downtify.playlist_catalog import PlaylistCatalog
from downtify.track_index import TrackIndex

TRACK_ID = '4uLU6hMCjMI75M1A2tKUQC'


@pytest.fixture(autouse=True)
def readable_metadata(monkeypatch):
    monkeypatch.setattr(
        health_mod,
        'read_audio_metadata',
        lambda path: {'title': 'Title', 'artist': 'Artist'},
    )


def _missing_catalog_row(
    downloads: Path,
    db: Path,
    *,
    track_id: str = TRACK_ID,
    filename: str = 'Artist/Track.mp3',
) -> PlaylistCatalog:
    catalog = PlaylistCatalog(db)
    full = downloads / filename
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(b'x')
    catalog.upsert_track('Mix', {'song_id': track_id}, filename, full)
    full.unlink()
    return catalog


def test_missing_referenced_track_is_missing_file(tmp_path: Path) -> None:
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    db = tmp_path / 'library.db'
    index = TrackIndex(db)
    index.register(TRACK_ID, 'Artist/Track.mp3')
    catalog = _missing_catalog_row(downloads, db)

    report = scan_library_health(
        LibraryContext(
            download_dir=downloads,
            track_index=index,
            playlist_catalog=catalog,
        ),
        track_index=index,
        playlist_catalog=catalog,
    )

    missing = [
        row for row in report['findings'] if row['category'] == 'missing_file'
    ]
    assert len(missing) == 1
    assert missing[0]['source'] == 'track_index'
    assert missing[0]['recommendation'] == 'redownload'


def test_unreferenced_missing_track_is_orphan_record(tmp_path: Path) -> None:
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    index = TrackIndex(tmp_path / 'library.db')
    index.register(TRACK_ID, 'Artist/Gone.mp3')

    report = scan_library_health(
        LibraryContext(download_dir=downloads, track_index=index),
        track_index=index,
    )

    assert report['findings'] == [
        {
            'id': f'track_index:{TRACK_ID}:Artist/Gone.mp3',
            'category': 'orphan_record',
            'severity': 'warning',
            'source': 'track_index',
            'file': 'Artist/Gone.mp3',
            'record_id': TRACK_ID,
            'recommendation': 'review_record',
        }
    ]


def test_moved_file_is_path_mismatch(tmp_path: Path) -> None:
    downloads = tmp_path / 'downloads'
    old = downloads / 'Old/Track.mp3'
    old.parent.mkdir(parents=True)
    old.write_bytes(b'same-bytes')
    index = TrackIndex(tmp_path / 'library.db')
    index.register(TRACK_ID, 'Old/Track.mp3', full_path=old)
    moved = downloads / 'Moved/Track.mp3'
    moved.parent.mkdir(parents=True)
    old.replace(moved)

    report = scan_library_health(
        LibraryContext(download_dir=downloads, track_index=index),
        track_index=index,
    )

    assert report['findings'] == [
        {
            'id': f'track_index:{TRACK_ID}:Old/Track.mp3',
            'category': 'path_mismatch',
            'severity': 'info',
            'source': 'track_index',
            'file': 'Old/Track.mp3',
            'record_id': TRACK_ID,
            'recommendation': 'reconcile_paths',
            'suggested_path': 'Moved/Track.mp3',
        }
    ]


def test_moved_index_without_key_uses_playlist_key(tmp_path: Path) -> None:
    downloads = tmp_path / 'downloads'
    old = downloads / 'Old/Track.mp3'
    old.parent.mkdir(parents=True)
    old.write_bytes(b'same-bytes')
    db = tmp_path / 'library.db'
    index = TrackIndex(db)
    index.register(TRACK_ID, 'Old/Track.mp3')
    catalog = PlaylistCatalog(db)
    catalog.upsert_track('Mix', {'song_id': TRACK_ID}, 'Old/Track.mp3', old)
    moved = downloads / 'Moved/Track.mp3'
    moved.parent.mkdir(parents=True)
    old.replace(moved)

    report = scan_library_health(
        LibraryContext(download_dir=downloads),
        track_index=index,
        playlist_catalog=catalog,
    )

    assert len(report['findings']) == 1
    assert report['findings'][0]['category'] == 'path_mismatch'
    assert report['findings'][0]['source'] == 'track_index'
    assert report['findings'][0]['suggested_path'] == 'Moved/Track.mp3'


def test_moved_playlist_without_key_uses_index_key(tmp_path: Path) -> None:
    downloads = tmp_path / 'downloads'
    old = downloads / 'Old/Track.mp3'
    old.parent.mkdir(parents=True)
    old.write_bytes(b'same-bytes')
    db = tmp_path / 'library.db'
    index = TrackIndex(db)
    index.register(TRACK_ID, 'Old/Track.mp3', full_path=old)
    catalog = PlaylistCatalog(db)
    catalog.upsert_track('Mix', {'song_id': TRACK_ID}, 'Old/Track.mp3', old)
    with sqlite3.connect(db) as conn:
        conn.execute('UPDATE playlist_tracks SET content_key = NULL')
    moved = downloads / 'Moved/Track.mp3'
    moved.parent.mkdir(parents=True)
    old.replace(moved)

    report = scan_library_health(
        LibraryContext(download_dir=downloads),
        track_index=index,
        playlist_catalog=catalog,
    )

    assert len(report['findings']) == 1
    assert report['findings'][0]['category'] == 'path_mismatch'
    assert report['findings'][0]['source'] == 'track_index'
    assert report['findings'][0]['suggested_path'] == 'Moved/Track.mp3'


def test_moved_monitor_file_uses_index_content_key(tmp_path: Path) -> None:
    downloads = tmp_path / 'downloads'
    old = downloads / 'Old/Track.mp3'
    old.parent.mkdir(parents=True)
    old.write_bytes(b'same-bytes')
    index = TrackIndex(tmp_path / 'library.db')
    index.register(TRACK_ID, 'Old/Track.mp3', full_path=old)
    watches = monitor_mod.PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = watches.add_playlist(
        'watch-1', 'Watch', 'https://example.test/watch'
    )
    watches.mark_track_downloaded(watch.id, TRACK_ID, 'Old/Track.mp3')
    moved = downloads / 'Moved/Track.mp3'
    moved.parent.mkdir(parents=True)
    old.replace(moved)

    report = scan_library_health(
        LibraryContext(download_dir=downloads),
        track_index=index,
        monitor_db=watches,
    )

    assert len(report['findings']) == 1
    assert report['findings'][0]['category'] == 'path_mismatch'
    assert report['findings'][0]['source'] == 'track_index'
    assert report['findings'][0]['suggested_path'] == 'Moved/Track.mp3'


def test_playlist_and_monitor_missing_files_are_reported(
    tmp_path: Path,
) -> None:
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    db = tmp_path / 'library.db'
    playlist_track = '6rqhFgbbKwnb9mlm3xDWRR'
    monitor_track = '3n3Ppam7vgaVa1iaRUc9Lp'
    catalog = _missing_catalog_row(
        downloads,
        db,
        track_id=playlist_track,
        filename='Playlist/Gone.mp3',
    )
    watches = monitor_mod.PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = watches.add_playlist(
        'watch-1', 'Watch', 'https://example.test/watch'
    )
    watches.mark_track_downloaded(watch.id, monitor_track, 'Monitor/Gone.mp3')

    report = scan_library_health(
        LibraryContext(download_dir=downloads),
        playlist_catalog=catalog,
        monitor_db=watches,
    )

    missing = [
        row for row in report['findings'] if row['category'] == 'missing_file'
    ]
    assert {(row['source'], row['file']) for row in missing} == {
        ('playlist', 'Playlist/Gone.mp3'),
        ('monitor', 'Monitor/Gone.mp3'),
    }
    assert all(row['recommendation'] == 'redownload' for row in missing)


def test_navidrome_missing_content_key_is_stale_mapping(
    tmp_path: Path,
) -> None:
    downloads = tmp_path / 'downloads'
    track = downloads / 'Artist/Track.mp3'
    track.parent.mkdir(parents=True)
    track.write_bytes(b'x')
    navidrome = NavidromeIndex(tmp_path / 'library.db')
    navidrome.store(
        'Artist/Track.mp3',
        'nd-1',
        spotify_track_id=TRACK_ID,
        full_path=track,
    )
    track.unlink()

    report = scan_library_health(
        LibraryContext(download_dir=downloads),
        navidrome_index=navidrome,
    )

    assert report['findings'] == [
        {
            'id': 'navidrome:nd-1:Artist/Track.mp3',
            'category': 'stale_mapping',
            'severity': 'warning',
            'source': 'navidrome',
            'file': 'Artist/Track.mp3',
            'record_id': 'nd-1',
            'recommendation': 'refresh_navidrome',
        }
    ]


def test_missing_title_or_artist_is_missing_metadata(
    tmp_path: Path, monkeypatch
) -> None:
    downloads = tmp_path / 'downloads'
    track = downloads / 'Artist - Title.mp3'
    track.parent.mkdir(parents=True)
    track.write_bytes(b'x')

    def metadata(path: Path) -> dict[str, object]:
        return {'title': '', 'artist': ''}

    monkeypatch.setattr(health_mod, 'read_audio_metadata', metadata)

    report = scan_library_health(LibraryContext(download_dir=downloads))

    assert len(report['findings']) == 1
    finding = report['findings'][0]
    assert finding['category'] == 'missing_metadata'
    assert finding['source'] == 'disk'
    assert finding['file'] == 'Artist - Title.mp3'
    assert finding['recommendation'] == 'repair_metadata'


def test_scan_is_read_only(tmp_path: Path) -> None:
    downloads = tmp_path / 'downloads'
    track = downloads / 'Artist/Track.mp3'
    track.parent.mkdir(parents=True)
    track.write_bytes(b'audio-bytes')
    db = tmp_path / 'library.db'
    index = TrackIndex(db)
    index.register(TRACK_ID, 'Artist/Track.mp3', full_path=track)
    catalog = PlaylistCatalog(db)
    catalog.upsert_track(
        'Mix', {'song_id': TRACK_ID}, 'Artist/Track.mp3', track
    )
    watches = monitor_mod.PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = watches.add_playlist(
        'watch-1', 'Watch', 'https://example.test/watch'
    )
    watches.mark_track_downloaded(watch.id, TRACK_ID, 'Artist/Track.mp3')
    navidrome = NavidromeIndex(db)
    navidrome.store(
        'Artist/Track.mp3', 'nd-1', spotify_track_id=TRACK_ID, full_path=track
    )
    before = (
        track.read_bytes(),
        sorted(
            path.relative_to(downloads)
            for path in downloads.rglob('*')
            if path.is_file()
        ),
        index.all_rows(),
        catalog.all_track_rows(),
        watches.list_all_downloaded_tracks(),
        navidrome.all_rows(),
    )
    ctx = LibraryContext(download_dir=downloads)

    scan_library_health(
        ctx,
        track_index=index,
        playlist_catalog=catalog,
        monitor_db=watches,
        navidrome_index=navidrome,
    )
    scan_library_health(
        ctx,
        track_index=index,
        playlist_catalog=catalog,
        monitor_db=watches,
        navidrome_index=navidrome,
    )

    assert track.read_bytes() == before[0]
    assert (
        sorted(
            path.relative_to(downloads)
            for path in downloads.rglob('*')
            if path.is_file()
        )
        == before[1]
    )
    assert index.all_rows() == before[2]
    assert catalog.all_track_rows() == before[3]
    assert watches.list_all_downloaded_tracks() == before[4]
    assert navidrome.all_rows() == before[5]


def test_redacted_export_contains_no_identifiers() -> None:
    secret_path = '/home/yeet/secret/Token.mp3'
    secret_id = '4uLU6hMCjMI75M1A2tKUQC'
    secret_url = 'https://private.example/token'
    report = {
        'version': 1,
        'scanned_at': '2026-11-25T00:00:00+00:00',
        'summary': {'findings': 1, 'by_category': {'missing_file': 1}},
        'sources': {'disk': True},
        'findings': [
            {
                'id': f'track_index:{secret_id}:{secret_path}',
                'category': 'missing_file',
                'severity': 'warning',
                'source': 'track_index',
                'file': secret_path,
                'record_id': secret_id,
                'recommendation': 'redownload',
                'suggested_path': secret_url,
            }
        ],
        'warnings': [],
    }

    redacted = health_mod.redact_health_report(report)

    assert redacted['summary']['findings'] == 1
    assert redacted['summary']['by_category']['missing_file'] == 1
    assert redacted['findings'] == [
        {
            'id': 1,
            'category': 'missing_file',
            'severity': 'warning',
            'source': 'track_index',
            'recommendation': 'redownload',
        }
    ]
    assert set(redacted['findings'][0]) == {
        'id',
        'category',
        'severity',
        'source',
        'recommendation',
    }
    assert all(
        secret not in str(redacted)
        for secret in (secret_path, secret_id, secret_url)
    )


def test_missing_download_root_is_partial_not_healthy(tmp_path: Path) -> None:
    index = TrackIndex(tmp_path / 'library.db')
    index.register(TRACK_ID, 'Artist/Missing.mp3')

    report = scan_library_health(
        LibraryContext(download_dir=tmp_path / 'missing'),
        track_index=index,
    )

    assert report['sources']['disk'] is False
    assert report['warnings'] == ['disk_unavailable']
    assert report['findings'] == []


def test_unavailable_external_folder_is_partial(tmp_path: Path) -> None:
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    index = TrackIndex(tmp_path / 'library.db')
    index.register(TRACK_ID, 'ext/nas/Artist/Track.mp3')

    report = scan_library_health(
        LibraryContext(
            download_dir=downloads,
            extra_dirs=(tmp_path / 'missing-nas',),
        ),
        track_index=index,
    )

    assert report['sources']['disk'] is False
    assert report['warnings'] == ['external_folder_unavailable']
    assert report['findings'] == []


def test_unavailable_reference_store_does_not_create_orphans(
    tmp_path: Path, monkeypatch
) -> None:
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    index = TrackIndex(tmp_path / 'library.db')
    index.register(TRACK_ID, 'Artist/Missing.mp3')
    catalog = PlaylistCatalog(tmp_path / 'library.db')

    def unavailable():
        raise OSError('database locked')

    monkeypatch.setattr(catalog, 'all_track_rows', unavailable)

    report = scan_library_health(
        LibraryContext(download_dir=downloads),
        track_index=index,
        playlist_catalog=catalog,
    )

    assert report['warnings'] == ['playlist_unavailable']
    assert report['findings'] == []


def test_repeated_metadata_failures_produce_one_warning(
    tmp_path: Path, monkeypatch
) -> None:
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    for name in ('one.mp3', 'two.mp3'):
        (downloads / name).write_bytes(b'x')

    def broken(path: Path) -> dict[str, object]:
        raise OSError('private path')

    monkeypatch.setattr(health_mod, 'read_audio_metadata', broken)

    report = scan_library_health(LibraryContext(download_dir=downloads))

    assert report['warnings'] == ['metadata_unavailable']


def test_redacted_export_keeps_only_known_warning_codes() -> None:
    redacted = health_mod.redact_health_report({
        'version': 1,
        'scanned_at': '2026-11-25T00:00:00+00:00',
        'summary': {},
        'sources': {},
        'findings': [],
        'warnings': [
            'disk_unavailable',
            'external_folder_unavailable',
            '/home/yeet/private',
        ],
    })

    assert redacted['warnings'] == [
        'disk_unavailable',
        'external_folder_unavailable',
    ]
    assert '/home/yeet/private' not in str(redacted)
