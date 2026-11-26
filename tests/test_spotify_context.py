import sqlite3

from downtify.spotify_context import (
    cache_name,
    context_kind,
    ensure_schema,
    labels_for,
    normalize_context,
)


def test_normalize_context_accepts_supported_spotify_forms():
    assert normalize_context('spotify:playlist:abc') == 'spotify:playlist:abc'
    assert (
        normalize_context('spotify:user:u:playlist:abc')
        == 'spotify:playlist:abc'
    )
    assert (
        normalize_context('https://open.spotify.com/playlist/abc?si=x')
        == 'spotify:playlist:abc'
    )
    assert (
        normalize_context('https://open.spotify.com/intl-tr/album/abc?si=x')
        == 'spotify:album:abc'
    )
    assert (
        normalize_context('https://api.spotify.com/v1/artists/abc')
        == 'spotify:artist:abc'
    )
    assert not normalize_context('Downtify Playlist')
    assert not normalize_context('https://example.com/playlist/abc')


def test_context_kind_uses_normalized_type():
    assert context_kind('spotify:user:u:playlist:abc') == 'playlist'
    assert context_kind('https://open.spotify.com/artist/abc') == 'artist'
    assert not context_kind('Downtify Playlist')


def test_labels_for_returns_only_cached_nonempty_names(tmp_path):
    db = tmp_path / 'activity.db'
    ensure_schema(db)
    cache_name(db, 'spotify:playlist:abc', 'Cached Playlist')
    cache_name(db, 'spotify:playlist:empty', '')

    assert labels_for(
        db,
        [
            'spotify:playlist:abc',
            'spotify:playlist:empty',
            'spotify:artist:missing',
        ],
    ) == {'spotify:playlist:abc': 'Cached Playlist'}


def test_labels_for_tolerates_missing_database_and_table(tmp_path):
    missing = tmp_path / 'missing.db'
    assert labels_for(missing, ['spotify:playlist:abc']) == {}
    assert not missing.exists()

    other = tmp_path / 'other.db'
    with sqlite3.connect(other) as conn:
        conn.execute('CREATE TABLE something_else (value TEXT)')
    assert labels_for(other, ['spotify:playlist:abc']) == {}


def test_cache_name_is_idempotent_and_updates_existing_name(tmp_path):
    db = tmp_path / 'activity.db'
    ensure_schema(db)
    cache_name(db, 'spotify:album:abc', 'Old Album')
    cache_name(db, 'spotify:album:abc', 'New Album')

    assert labels_for(db, ['spotify:album:abc']) == {
        'spotify:album:abc': 'New Album'
    }
    with sqlite3.connect(db) as conn:
        assert (
            conn.execute(
                'SELECT COUNT(*) FROM spotify_context_cache'
            ).fetchone()[0]
            == 1
        )
