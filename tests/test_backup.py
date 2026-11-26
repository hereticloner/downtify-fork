from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from downtify import backup as backup_module
from downtify import (
    collections,
    lastfm_history,
    monitor,
    spotify_context,
    spotify_history,
)
from downtify.backup import BackupStore
from downtify.download_queue import PendingDownload, PendingDownloads
from downtify.likes import LikedTracks
from downtify.listening_history import ListeningStore
from downtify.playback import PlaybackStore
from downtify.playlist_catalog import PlaylistCatalog
from downtify.sqlite_utils import connect_sqlite
from downtify.track_index import TrackIndex
from downtify.users import UserStore


def _seed(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / 'settings.json').write_text(
        json.dumps({'format': 'flac', 'notifications': {'enabled': True}})
    )
    (data_dir / 'notifications.json').write_text(
        json.dumps({
            'version': 1,
            'channels': {'telegram': {'bot_token': 'secret'}},
        })
    )
    users = UserStore(data_dir / 'downtify.db')
    user = users.create('alice', 'password123', role='user')
    users.set_preferences(user['id'], {'theme': 'dark', 'locale': 'tr'})

    library = data_dir / 'downtify_library.db'
    tracks = TrackIndex(library)
    tracks.register('0TnOYISbd1XYRBk9myaseg', 'Artist/Song.mp3')
    liked = LikedTracks(library)
    liked.like('Artist/Song.mp3', title='Song', artist='Artist')
    catalog = PlaylistCatalog(library)
    catalog.ensure_playlist('Mix', spotify_id='playlist-1')
    catalog.upsert_track(
        'Mix',
        {'song_id': '0TnOYISbd1XYRBk9myaseg'},
        'Artist/Song.mp3',
        data_dir / 'Artist' / 'Song.mp3',
        track_order=1,
    )
    queue = PendingDownloads(library)
    queue.add([
        PendingDownload(
            song_id='0TnOYISbd1XYRBk9myaseg',
            song={'song_id': '0TnOYISbd1XYRBk9myaseg', 'name': 'Song'},
            options={'playlist_name': 'Mix'},
            user_ids=[user['id']],
        )
    ])
    queue.set_paused(True)

    watches = monitor.PlaylistMonitorDB(data_dir / 'downtify_monitor.db')
    watches.add_playlist(
        'playlist-1', 'Mix', 'https://open.spotify.com/playlist/playlist-1'
    )
    with watches._connect() as conn:
        conn.execute(
            'INSERT INTO download_policy (id, track_id, title, artist, album, '
            'duration, title_key, artist_key, album_key, fallback_key, blocked, '
            "reason, updated) VALUES ('policy-1','0TnOYISbd1XYRBk9myaseg',"
            "'Song','Artist','Album',180,'song','artist','album','',1,'manual',1)"
        )

    playback = PlaybackStore(data_dir / 'downtify_activity.db')
    playback.report(
        user_id=user['id'],
        device_id='phone',
        player='web',
        state='playing',
        track={'track_id': '0TnOYISbd1XYRBk9myaseg', 'title': 'Song'},
        position=42,
    )

    downloads = data_dir / 'downloads'
    downloads.mkdir()
    collections.create_collection(downloads, 'Favourites')
    (downloads / 'Playlists' / '.collections' / 'Favourites.json').write_text(
        json.dumps({
            'version': 1,
            'name': 'Favourites',
            'playlists': ['Mix'],
            'rules': [{'type': 'playlist_contains', 'value': 'Song'}],
        })
    )


def _read_backup(path: Path) -> dict:
    with gzip.open(path, 'rt', encoding='utf-8') as handle:
        return json.load(handle)


def test_backup_contains_metadata_and_no_audio_or_sessions(tmp_path):
    data_dir = tmp_path / 'data'
    _seed(data_dir)
    (data_dir / 'downloads' / 'Artist').mkdir()
    (data_dir / 'downloads' / 'Artist' / 'Song.mp3').write_bytes(b'audio')
    store = BackupStore(data_dir)

    path = store.write()
    doc = _read_backup(path)

    assert doc['version'] == 1
    assert doc['settings']['format'] == 'flac'
    assert (
        doc['notification_secrets']['channels']['telegram']['bot_token']
        == 'secret'
    )
    assert doc['sqlite']['downtify.db']['users'][0]['username'] == 'alice'
    assert doc['sqlite']['downtify.db']['users'][0]['password_hash']
    assert 'auth_sessions' not in doc['sqlite']['downtify.db']
    assert (
        doc['sqlite']['downtify_library.db']['library_tracks'][0]['filename']
        == 'Artist/Song.mp3'
    )
    assert (
        doc['sqlite']['downtify_library.db']['liked_tracks'][0]['stored_path']
        == 'Artist/Song.mp3'
    )
    assert (
        doc['sqlite']['downtify_library.db']['pending_downloads'][0]['song_id']
        == '0TnOYISbd1XYRBk9myaseg'
    )
    assert (
        doc['sqlite']['downtify_monitor.db']['monitored_playlists'][0]['name']
        == 'Mix'
    )
    assert (
        doc['sqlite']['downtify_monitor.db']['download_policy'][0]['blocked']
        == 1
    )
    assert (
        doc['sqlite']['downtify_activity.db']['playback_positions'][0][
            'position'
        ]
        == 42
    )
    assert doc['collections'][0]['playlists'] == ['Mix']
    assert 'audio' not in json.dumps(doc)
    assert not any(key == 'audio_bytes' for key in doc)


def test_backup_restores_unified_history_and_raw_provider_rows(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    db = source / 'downtify_activity.db'
    listening = ListeningStore(db)
    spotify_history.save_recently_played(
        db,
        [
            {
                'played_at': '2026-11-25T20:15:00Z',
                'spotify_track_id': 's1',
                'track_name': 'T',
                'artist_name': 'A',
                'raw_item': {'id': 's1', 'external_ids': {'isrc': 'ISRC1'}},
            }
        ],
        user_id=1,
    )
    lastfm_history.save_recent_tracks(
        db,
        [
            {
                'played_at': '2026-11-25T21:15:00+00:00',
                'uts': 1795631700,
                'artist_name': 'B',
                'track_name': 'U',
                'raw_item': {'name': 'U', 'artist': {'name': 'B'}},
            }
        ],
        user_id=1,
    )
    spotify_history.link_pending(db, listening, user_id=1)
    lastfm_history.link_pending(db, listening, user_id=1)
    lastfm_history._save_state(
        db,
        {
            'newest_at': '2026-11-25T21:15:00+00:00',
            'oldest_at': '2026-11-20T21:15:00+00:00',
            'backfill_done': False,
        },
    )
    path = BackupStore(source).write()

    target = tmp_path / 'target'
    target.mkdir()
    BackupStore(target).restore(path, dry_run=False, requeue_missing=False)

    with connect_sqlite(
        target / 'downtify_activity.db', row_factory=True
    ) as conn:
        assert (
            conn.execute('SELECT COUNT(*) FROM listening_events').fetchone()[0]
            == 2
        )
        assert (
            conn.execute(
                'SELECT COUNT(*) FROM listening_event_sources'
            ).fetchone()[0]
            == 2
        )
        raw = conn.execute(
            'SELECT raw_json FROM spotify_recently_played'
        ).fetchone()[0]
        assert json.loads(raw)['external_ids']['isrc'] == 'ISRC1'
        assert (
            conn.execute(
                'SELECT COUNT(*) FROM lastfm_recent_tracks'
            ).fetchone()[0]
            == 1
        )
        state = conn.execute(
            "SELECT newest_at FROM history_import_state WHERE source='lastfm'"
        ).fetchone()[0]
        assert state == '2026-11-25T21:15:00+00:00'


def test_backup_restores_spotify_context_cache(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    db = source / 'downtify_activity.db'
    spotify_context.ensure_schema(db)
    spotify_context.cache_name(db, 'spotify:playlist:abc', 'Cached Playlist')

    path = BackupStore(source).write()
    target = tmp_path / 'target'
    target.mkdir()
    BackupStore(target).restore(path, dry_run=False, requeue_missing=False)

    assert spotify_context.labels_for(
        target / 'downtify_activity.db', ['spotify:playlist:abc']
    ) == {'spotify:playlist:abc': 'Cached Playlist'}


def test_backup_rotation_keeps_two_private_atomic_files(tmp_path):
    store = BackupStore(tmp_path / 'data')
    paths = [store.write() for _ in range(3)]
    assert paths[0] != paths[1] != paths[2]
    assert sorted(path.name for path in store.list()) == sorted(
        path.name for path in paths[1:]
    )
    for path in store.list():
        assert path.stat().st_mode & 0o777 == 0o600
        assert _read_backup(path)['version'] == 1
    assert not list(store.backup_dir.glob('*.partial'))


def test_restore_dry_run_is_additive_and_preserves_existing_rows(tmp_path):
    source = tmp_path / 'source'
    _seed(source)
    backup = BackupStore(source).write()

    target = tmp_path / 'target'
    _seed(target)
    with connect_sqlite(target / 'downtify.db', row_factory=True) as conn:
        conn.execute(
            'UPDATE users SET prefs_json=\'{"theme":"light"}\' WHERE username=\'alice\''
        )
    (
        target / 'downloads' / 'Playlists' / '.collections' / 'Favourites.json'
    ).write_text(
        json.dumps({
            'version': 1,
            'name': 'Favourites',
            'playlists': ['Local'],
        })
    )
    store = BackupStore(target)

    preview = store.preview(backup)
    assert preview['settings']['format'] == 'flac'
    counts = {
        'users': 0,
        'library_tracks': 0,
        'liked_tracks': 0,
        'playlists': 0,
        'pending_downloads': 0,
        'monitored_playlists': 0,
        'playback_positions': 0,
        'collections': 0,
    }
    result = store.restore(backup, dry_run=True)

    assert result['dry_run'] is True
    for table, count in counts.items():
        assert result['added'][table] == count
    with connect_sqlite(target / 'downtify.db', row_factory=True) as conn:
        assert (
            json.loads(
                conn.execute(
                    "SELECT prefs_json FROM users WHERE username='alice'"
                ).fetchone()[0]
            )['theme']
            == 'light'
        )
    assert collections.get_collection(target / 'downloads', 'Favourites')[
        'playlists'
    ] == ['Local']


def test_restore_adds_missing_rows_and_requeues_only_identified_songs(
    tmp_path,
):
    source = tmp_path / 'source'
    _seed(source)
    backup = BackupStore(source).write()
    target = tmp_path / 'target'
    target.mkdir()
    store = BackupStore(target)

    result = store.restore(backup, dry_run=False, requeue_missing=True)

    assert result['dry_run'] is False
    assert result['added']['users'] == 1
    assert result['requeued'] == ['0TnOYISbd1XYRBk9myaseg']
    assert result['unresolved'] == []
    assert (target / 'settings.json').exists()
    assert (target / 'notifications.json').stat().st_mode & 0o777 == 0o600
    with connect_sqlite(
        target / 'downtify_library.db', row_factory=True
    ) as conn:
        assert (
            conn.execute('SELECT COUNT(*) FROM pending_downloads').fetchone()[
                0
            ]
            == 1
        )
        assert (
            conn.execute('SELECT COUNT(*) FROM library_tracks').fetchone()[0]
            == 1
        )
    assert collections.get_collection(target / 'downloads', 'Favourites')[
        'playlists'
    ] == ['Mix']


def test_restore_preserves_existing_settings_and_secret_values(tmp_path):
    source = tmp_path / 'source'
    _seed(source)
    (source / 'settings.json').write_text(
        json.dumps({
            'format': 'flac',
            'bitrate': '320',
            'notifications': {
                'enabled': True,
                'channels': {
                    'telegram': {
                        'enabled': True,
                        'events': ['download.failed'],
                    },
                    'webhook': {
                        'enabled': True,
                        'url': 'https://evil.test/hook',
                    },
                },
            },
        })
    )
    (source / 'notifications.json').write_text(
        json.dumps({
            'version': 1,
            'channels': {
                'telegram': {'bot_token': 'backup-token', 'chat_id': '11'},
                'webhook': {'url': 'https://evil.test/hook', 'token': 'evil'},
            },
        })
    )
    backup = BackupStore(source).write()

    target = tmp_path / 'target'
    target.mkdir()
    settings_path = target / 'settings.json'
    secrets_path = target / 'notifications.json'
    settings_path.write_text(
        json.dumps({
            'format': 'mp3',
            'notifications': {
                'enabled': False,
                'channels': {
                    'telegram': {
                        'enabled': False,
                        'events': ['watch.downloaded'],
                    },
                    'webhook': {'enabled': False},
                },
            },
        })
    )
    secrets_path.write_text(
        json.dumps({
            'version': 1,
            'channels': {
                'telegram': {'bot_token': 'current-token', 'chat_id': '42'},
                'webhook': {'url': 'https://current.test/hook'},
            },
        })
    )

    BackupStore(target).restore(backup, dry_run=False)

    settings = json.loads(settings_path.read_text())
    secrets = json.loads(secrets_path.read_text())
    assert settings['format'] == 'mp3'
    assert settings['bitrate'] == '320'
    assert settings['notifications']['enabled'] is False
    assert (
        settings['notifications']['channels']['telegram']['enabled'] is False
    )
    assert secrets['channels']['telegram']['bot_token'] == 'current-token'
    assert secrets['channels']['telegram']['chat_id'] == '42'
    assert secrets['channels']['webhook']['url'] == 'https://current.test/hook'
    assert secrets['channels']['webhook']['token'] == 'evil'
    assert 'evil.test' not in settings_path.read_text()


def test_restore_leaves_fully_populated_json_files_byte_for_byte(tmp_path):
    source = tmp_path / 'source'
    _seed(source)
    backup = BackupStore(source).write()
    target = tmp_path / 'target'
    _seed(target)
    settings_before = (target / 'settings.json').read_bytes()
    secrets_before = (target / 'notifications.json').read_bytes()

    BackupStore(target).restore(backup, dry_run=False)

    assert (target / 'settings.json').read_bytes() == settings_before
    assert (target / 'notifications.json').read_bytes() == secrets_before


def test_backup_restores_custom_collection_covers(tmp_path):
    source = tmp_path / 'source'
    _seed(source)
    collection = collections.create_collection(source / 'downloads', 'Covered')
    cover = (
        source
        / 'downloads'
        / 'Playlists'
        / '.collections'
        / 'covers'
        / 'Covered.jpg'
    )
    cover.parent.mkdir(parents=True)
    cover.write_bytes(b'custom-cover')
    collection['cover'] = cover.name
    (
        source / 'downloads' / 'Playlists' / '.collections' / 'Covered.json'
    ).write_text(json.dumps(collection))
    backup = BackupStore(source).write()
    target = tmp_path / 'target'

    BackupStore(target).restore(backup, dry_run=False)

    restored = (
        target
        / 'downloads'
        / 'Playlists'
        / '.collections'
        / 'covers'
        / 'Covered.jpg'
    )
    assert restored.read_bytes() == b'custom-cover'


def test_restore_rejects_collection_path_traversal(tmp_path):
    source = tmp_path / 'source'
    _seed(source)
    doc = _read_backup(BackupStore(source).write())
    doc['collections'] = [
        {
            'version': 1,
            'name': '../../../escape.json',
            'playlists': [],
        }
    ]
    backup = source / 'backups' / 'downtify-traversal.json.gz'
    with gzip.open(backup, 'wt', encoding='utf-8') as handle:
        json.dump(doc, handle)
    target = tmp_path / 'target'
    target.mkdir()

    result = BackupStore(target).restore(backup, dry_run=False)

    assert result['invalid_collections'] == ['../../../escape.json']
    assert not (target / 'escape.json').exists()


def test_restore_rolls_back_all_tables_in_a_database_on_failure(
    tmp_path, monkeypatch
):
    source = tmp_path / 'source'
    _seed(source)
    backup = BackupStore(source).write()
    target = tmp_path / 'target'
    target.mkdir()
    store = BackupStore(target)
    original = backup_module._insert_missing

    def fail_second(conn, table, rows, keys):
        if table == 'liked_tracks':
            raise OSError('disk full')
        return original(conn, table, rows, keys)

    monkeypatch.setattr(backup_module, '_insert_missing', fail_second)
    with pytest.raises(OSError, match='disk full'):
        store.restore(backup, dry_run=False)

    with connect_sqlite(
        target / 'downtify_library.db', row_factory=True
    ) as conn:
        assert (
            conn.execute('SELECT COUNT(*) FROM library_tracks').fetchone()[0]
            == 0
        )
        assert (
            conn.execute('SELECT COUNT(*) FROM liked_tracks').fetchone()[0]
            == 0
        )


def test_restore_does_not_requeue_a_track_already_on_disk(tmp_path):
    source = tmp_path / 'source'
    _seed(source)
    backup = BackupStore(source).write()
    target = tmp_path / 'target'
    (target / 'downloads' / 'Artist').mkdir(parents=True)
    (target / 'downloads' / 'Artist' / 'Song.mp3').write_bytes(b'audio')

    result = BackupStore(target).restore(
        backup, dry_run=False, requeue_missing=True
    )

    assert result['requeued'] == []
    with connect_sqlite(
        target / 'downtify_library.db', row_factory=True
    ) as conn:
        assert (
            conn.execute('SELECT COUNT(*) FROM pending_downloads').fetchone()[
                0
            ]
            == 0
        )


def test_restore_keeps_missing_paused_jobs_paused(tmp_path):
    source = tmp_path / 'source'
    _seed(source)
    queue = PendingDownloads(source / 'downtify_library.db')
    queue.set_jobs_paused(['0TnOYISbd1XYRBk9myaseg'], True)
    backup = BackupStore(source).write()
    target = tmp_path / 'target'

    result = BackupStore(target).restore(
        backup, dry_run=False, requeue_missing=True
    )

    assert result['requeued'] == []
    rows = PendingDownloads(target / 'downtify_library.db').rows()
    assert len(rows) == 1
    assert rows[0].paused is True


def test_restore_rolls_back_json_files_when_a_later_write_fails(
    tmp_path, monkeypatch
):
    source = tmp_path / 'source'
    _seed(source)
    backup = BackupStore(source).write()
    target = tmp_path / 'target'
    _seed(target)
    (target / 'settings.json').write_text(json.dumps({'format': 'mp3'}))
    settings_before = (target / 'settings.json').read_bytes()
    secrets_before = (target / 'notifications.json').read_bytes()
    original = backup_module._atomic_json

    def fail_settings(path, data):
        if path.name == 'settings.json':
            raise OSError('disk full')
        return original(path, data)

    monkeypatch.setattr(backup_module, '_atomic_json', fail_settings)
    with pytest.raises(OSError, match='disk full'):
        BackupStore(target).restore(backup, dry_run=False)

    assert (target / 'settings.json').read_bytes() == settings_before
    assert (target / 'notifications.json').read_bytes() == secrets_before


def test_restore_lists_songs_without_stable_spotify_identity(tmp_path):
    source = tmp_path / 'source'
    _seed(source)
    doc = _read_backup(BackupStore(source).write())
    doc['sqlite']['downtify_library.db']['library_tracks'][0][
        'spotify_track_id'
    ] = 'youtube-id'
    doc['sqlite']['downtify_library.db']['pending_downloads'][0]['song_id'] = (
        'youtube-id'
    )
    doc['sqlite']['downtify_library.db']['pending_downloads'][0]['song'] = {
        'name': 'Unknown'
    }
    backup = source / 'backups' / 'downtify-manual.json.gz'
    with gzip.open(backup, 'wt', encoding='utf-8') as handle:
        json.dump(doc, handle)

    result = BackupStore(tmp_path / 'target').restore(
        backup, dry_run=False, requeue_missing=True
    )

    assert result['requeued'] == []
    assert result['unresolved'] == ['youtube-id']
    with connect_sqlite(
        tmp_path / 'target' / 'downtify_library.db', row_factory=True
    ) as conn:
        assert (
            conn.execute('SELECT COUNT(*) FROM pending_downloads').fetchone()[
                0
            ]
            == 0
        )


def test_backup_limit_covers_measured_lastfm_archive():
    # A live 200-row sample averaged 1,296 bytes per raw scrobble; the
    # connected account's 98,601 rows therefore need about 122 MiB before
    # JSON escaping and the rest of the metadata backup.
    assert backup_module.MAX_BACKUP_BYTES >= 128 * 1024 * 1024


def test_preview_rejects_decompressed_bomb(tmp_path, monkeypatch):
    monkeypatch.setattr(backup_module, 'MAX_BACKUP_BYTES', 1024)
    store = BackupStore(tmp_path / 'data')
    bomb = store.backup_dir / 'downtify-bomb.json.gz'
    bomb.parent.mkdir(parents=True)
    with gzip.open(bomb, 'wt', encoding='utf-8') as handle:
        json.dump({'version': 1, 'sqlite': {}, 'padding': 'x' * 2048}, handle)

    with pytest.raises(ValueError, match='too large'):
        store.preview(bomb)


def test_preview_rejects_corrupt_and_future_versions(tmp_path):
    store = BackupStore(tmp_path / 'data')
    bad = store.backup_dir / 'downtify-bad.json.gz'
    bad.parent.mkdir(parents=True)
    with gzip.open(bad, 'wt', encoding='utf-8') as handle:
        handle.write('{broken')
    with pytest.raises(ValueError, match='corrupt'):
        store.preview(bad)

    future = store.backup_dir / 'downtify-future.json.gz'
    with gzip.open(future, 'wt', encoding='utf-8') as handle:
        json.dump({'version': 999}, handle)
    with pytest.raises(ValueError, match='version'):
        store.preview(future)
