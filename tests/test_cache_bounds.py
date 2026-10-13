"""The process-lifetime caches are capped (memory-leak guard).

Every dict exercised here is built once at import time (or once per
``Downloader``, which the app also builds exactly once) and is never
emptied except by the caps below, so a server that resolves many
artists, albums, tracks or handles would otherwise grow them without
limit. The same shape already shipped in
``artist_photo_proxy._url_cache``: drop the oldest entry (dicts keep
insertion order) just before writing a new one.

A cap is a memory ceiling only, never a behaviour change: a key asked
for twice in a row is still answered from the cache the second time.
That is what the ``*_still_answers_the_second_call`` tests pin down.

Nothing here touches the network - the HTTP layer is injected.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from downtify import (
    api,
    artist_profile,
    itunes,
    providers,
)
from downtify import (
    downloader as downloader_mod,
)

# ── iTunes: genre + artwork caches ──────────────────────────────────


def _track_row(artist: str, title: str, genre: str = 'Pop') -> dict:
    return {
        'wrapperType': 'track',
        'kind': 'song',
        'artistName': artist,
        'trackName': title,
        'primaryGenreName': genre,
        'artworkUrl100': (
            f'https://is1.mzstatic.com/image/{artist}/100x100bb.jpg'
        ),
    }


def _song(artist: str, title: str, album: str) -> dict:
    return {
        'name': title,
        'artists': [artist],
        'album_name': album,
    }


def _itunes_key(song: dict) -> str:
    return itunes._album_cache_key(song['artists'][0], song['album_name'])


async def _stub_search(query, limit=5):
    """Stands in for ``itunes._search_itunes`` (async since the rate
    pacing moved onto the event loop)."""

    return [_track_row(query, query)]


@pytest.fixture(autouse=True)
def _clean_itunes_caches():
    itunes._genre_cache.clear()
    itunes._artwork_cache.clear()
    yield
    itunes._genre_cache.clear()
    itunes._artwork_cache.clear()


def test_genre_cache_is_capped_and_drops_the_oldest(monkeypatch):
    monkeypatch.setattr(itunes, '_MAX_CACHE_ENTRIES', 3)
    monkeypatch.setattr(itunes, '_search_itunes', _stub_search)
    songs = [
        _song(f'Artist {i}', f'Track {i}', f'Album {i}') for i in range(5)
    ]
    for song in songs:
        itunes.fetch_genre(song)

    cache = itunes._genre_cache
    assert len(cache) == 3
    assert _itunes_key(songs[0]) not in cache
    assert _itunes_key(songs[-1]) in cache


def test_genre_cache_still_answers_the_second_call(monkeypatch):
    calls: list[str] = []

    async def search(query, limit=5):
        calls.append(query)
        return [_track_row('Paramore', 'The Real Thing')]

    monkeypatch.setattr(itunes, '_search_itunes', search)
    song = _song('Paramore', 'The Real Thing', 'Paramore')
    assert itunes.fetch_genre(song) == 'Pop'
    assert itunes.fetch_genre(song) == 'Pop'
    assert len(calls) == 1


def test_artwork_cache_is_capped_and_drops_the_oldest(monkeypatch):
    monkeypatch.setattr(itunes, '_MAX_CACHE_ENTRIES', 3)
    monkeypatch.setattr(itunes, '_search_itunes', _stub_search)
    songs = [
        _song(f'Artist {i}', f'Track {i}', f'Album {i}') for i in range(5)
    ]
    for song in songs:
        itunes.fetch_artwork_url(song)

    cache = itunes._artwork_cache
    assert len(cache) == 3
    assert _itunes_key(songs[0]) not in cache
    assert _itunes_key(songs[-1]) in cache


def test_artwork_cache_still_answers_the_second_call(monkeypatch):
    calls: list[str] = []

    async def search(query, limit=5):
        calls.append(query)
        return [_track_row('Paramore', 'The Real Thing')]

    monkeypatch.setattr(itunes, '_search_itunes', search)
    song = _song('Paramore', 'The Real Thing', 'Paramore')
    first = itunes.fetch_artwork_url(song, 1200)
    assert first.endswith('/1200x1200bb.jpg')
    assert itunes.fetch_artwork_url(song, 1200) == first
    assert len(calls) == 1


# ── YouTube Music provider caches ──────────────────────────────────

_PROVIDER_CACHES = (
    providers._album_track_cache,
    providers._album_meta_cache,
    providers._album_browse_search_cache,
    providers._album_search_artist_cache,
    providers._omv_preference_cache,
    providers._channel_id_cache,
)


class _FakeYtm:
    """Stands in for the ``YTMusic`` client; records every call."""

    def __init__(self) -> None:
        self.album_calls: list[str] = []
        self.search_calls: list[str] = []
        self.resolve_calls: list[str] = []
        self.album_title = ''
        self.browse_id = 'resolved-bid'
        self.channel_id = 'UC0000000000000000000000'

    def get_album(self, browse_id: str) -> dict:
        self.album_calls.append(browse_id)
        return {
            'tracks': [],
            'trackCount': 0,
            'title': f'Album {browse_id}',
            'year': '2020',
            'thumbnails': [],
            'type': 'Album',
            'artists': [{'name': 'Paramore'}],
        }

    def search(self, query: str, filter=None, limit=20):
        self.search_calls.append(query)
        if filter == 'albums':
            return [{'browseId': self.browse_id, 'title': self.album_title}]
        return []

    def _send_request(self, endpoint: str, payload):
        self.resolve_calls.append(endpoint)
        return {'endpoint': {'browseEndpoint': {'browseId': self.channel_id}}}


@pytest.fixture(autouse=True)
def _clean_provider_caches():
    for cache in _PROVIDER_CACHES:
        cache.clear()
    yield
    for cache in _PROVIDER_CACHES:
        cache.clear()


def _use_fake_ytm(monkeypatch) -> _FakeYtm:
    fake = _FakeYtm()
    monkeypatch.setattr(providers, '_ytm', lambda: fake)
    return fake


def test_album_caches_are_capped_and_drop_the_oldest(monkeypatch):
    monkeypatch.setattr(providers, '_CACHE_LIMIT', 3)
    _use_fake_ytm(monkeypatch)
    for i in range(5):
        providers._cached_album_tracks_and_count(f'bid-{i}')

    assert list(providers._album_track_cache) == ['bid-2', 'bid-3', 'bid-4']
    assert list(providers._album_meta_cache) == ['bid-2', 'bid-3', 'bid-4']


def test_album_cache_still_answers_the_second_call(monkeypatch):
    fake = _use_fake_ytm(monkeypatch)
    providers._cached_album_tracks_and_count('bid-1')
    assert providers._cached_album_tracks_and_count('bid-1') == ([], None)
    assert fake.album_calls == ['bid-1']
    assert providers._cached_album_meta('bid-1')['title'] == 'Album bid-1'


def test_album_search_artist_cache_is_capped_and_drops_oldest(
    monkeypatch,
):
    monkeypatch.setattr(providers, '_CACHE_LIMIT', 3)
    for i in range(5):
        providers._album_summary({
            'browseId': f'bid-{i}',
            'title': f'Album {i}',
            'artists': [{'name': f'Artist {i}'}],
        })

    cache = providers._album_search_artist_cache
    assert list(cache) == ['bid-2', 'bid-3', 'bid-4']
    assert cache['bid-4'] == ['Artist 4']


def test_album_browse_search_cache_is_capped_and_drops_oldest(monkeypatch):
    monkeypatch.setattr(providers, '_CACHE_LIMIT', 3)
    fake = _use_fake_ytm(monkeypatch)
    for i in range(5):
        fake.album_title = f'Album {i}'
        fake.browse_id = f'bid-{i}'
        match = {
            'album': {'name': f'Album {i}'},
            'artists': [{'name': f'Artist {i}'}],
        }
        found = providers._album_browse_id_from_search(match, None)
        assert found == f'bid-{i}'

    assert list(providers._album_browse_search_cache.values()) == [
        'bid-2',
        'bid-3',
        'bid-4',
    ]


def test_album_browse_search_cache_still_answers_second_call(monkeypatch):
    fake = _use_fake_ytm(monkeypatch)
    fake.album_title = 'Album 7'
    fake.browse_id = 'bid-7'
    match = {'album': {'name': 'Album 7'}, 'artists': [{'name': 'Artist 7'}]}
    assert providers._album_browse_id_from_search(match, None) == 'bid-7'
    assert providers._album_browse_id_from_search(match, None) == 'bid-7'
    assert len(fake.search_calls) == 1


def test_omv_preference_cache_is_capped_and_drops_the_oldest(monkeypatch):
    monkeypatch.setattr(providers, '_CACHE_LIMIT', 3)
    fake = _use_fake_ytm(monkeypatch)
    for i in range(5):
        providers._prefer_official_audio_track(
            f'omv-{i}',
            100,
            f'Track {i}',
            [f'Artist {i}'],
            providers._MUSIC_VIDEO_TYPE_MUSIC_VIDEO,
        )

    assert list(providers._omv_preference_cache) == [
        'omv-2',
        'omv-3',
        'omv-4',
    ]
    assert len(fake.search_calls) == 5


def test_omv_preference_cache_still_answers_the_second_call(monkeypatch):
    fake = _use_fake_ytm(monkeypatch)
    providers._prefer_official_audio_track(
        'omv-1',
        100,
        'Track 1',
        ['Artist 1'],
        providers._MUSIC_VIDEO_TYPE_MUSIC_VIDEO,
    )
    assert providers._prefer_official_audio_track(
        'omv-1',
        100,
        'Track 1',
        ['Artist 1'],
        providers._MUSIC_VIDEO_TYPE_MUSIC_VIDEO,
    ) == ('omv-1', 100)
    assert len(fake.search_calls) == 1


def test_channel_id_cache_is_capped_and_drops_the_oldest(monkeypatch):
    monkeypatch.setattr(providers, '_CACHE_LIMIT', 3)
    fake = _use_fake_ytm(monkeypatch)
    for i in range(5):
        fake.channel_id = f'UC{i:022d}'
        resolved = providers.resolve_artist_channel_id(f'@handle{i}')
        assert resolved == f'UC{i:022d}'

    cache = providers._channel_id_cache
    assert len(cache) == 3
    assert '@handle0' not in cache
    assert cache['@handle4'] == f'UC{4:022d}'


def test_channel_id_cache_still_answers_the_second_call(monkeypatch):
    fake = _use_fake_ytm(monkeypatch)
    fake.channel_id = 'UC0000000000000000000001'
    first = providers.resolve_artist_channel_id('@handle')
    assert providers.resolve_artist_channel_id('@handle') == first
    assert len(fake.resolve_calls) == 1


# ── Artist profile / top songs: per-artist lock dicts ──────────────


@pytest.fixture(autouse=True)
def _clean_profile_locks():
    artist_profile._seed_locks.clear()
    artist_profile._top_songs_locks.clear()
    yield
    artist_profile._seed_locks.clear()
    artist_profile._top_songs_locks.clear()


def test_seed_locks_are_capped_and_drop_the_oldest(tmp_path, monkeypatch):
    monkeypatch.setattr(artist_profile, '_MAX_LOCKS', 3)
    for i in range(5):
        artist_profile._seed_lock_for(tmp_path, f'Artist {i}')

    locks = artist_profile._seed_locks
    assert len(locks) == 3
    assert artist_profile._seed_key(tmp_path, 'Artist 0') not in locks
    assert artist_profile._seed_key(tmp_path, 'Artist 4') in locks


def test_seed_lock_is_the_same_object_for_the_same_artist(tmp_path):
    first = artist_profile._seed_lock_for(tmp_path, 'Paramore')
    assert artist_profile._seed_lock_for(tmp_path, 'paramore') is first
    assert len(artist_profile._seed_locks) == 1


def test_seed_locks_never_evict_a_lock_in_use(tmp_path, monkeypatch):
    monkeypatch.setattr(artist_profile, '_MAX_LOCKS', 2)
    held = artist_profile._seed_lock_for(tmp_path, 'Busy')
    with held:
        for i in range(4):
            artist_profile._seed_lock_for(tmp_path, f'Artist {i}')

    locks = artist_profile._seed_locks
    assert artist_profile._seed_key(tmp_path, 'Busy') in locks
    assert locks[artist_profile._seed_key(tmp_path, 'Busy')] is held
    assert len(locks) <= 2


def test_top_songs_locks_are_capped_and_drop_the_oldest(tmp_path, monkeypatch):
    monkeypatch.setattr(artist_profile, '_MAX_LOCKS', 3)
    for i in range(5):
        artist_profile._profile_top_songs_lock_for(tmp_path, f'Artist {i}')

    locks = artist_profile._top_songs_locks
    assert len(locks) == 3
    oldest = artist_profile.profile_top_songs_path_for(tmp_path, 'Artist 0')
    newest = artist_profile.profile_top_songs_path_for(tmp_path, 'Artist 4')
    assert str(oldest).lower() not in locks
    assert str(newest).lower() in locks


def test_top_songs_lock_is_the_same_object_for_the_same_artist(tmp_path):
    first = artist_profile._profile_top_songs_lock_for(tmp_path, 'Paramore')
    second = artist_profile._profile_top_songs_lock_for(tmp_path, 'paramore')
    assert second is first
    assert len(artist_profile._top_songs_locks) == 1


def test_top_songs_locks_never_evict_a_lock_in_use(tmp_path, monkeypatch):
    monkeypatch.setattr(artist_profile, '_MAX_LOCKS', 2)
    held = artist_profile._profile_top_songs_lock_for(tmp_path, 'Busy')
    key = str(
        artist_profile.profile_top_songs_path_for(tmp_path, 'Busy')
    ).lower()
    with held:
        for i in range(4):
            artist_profile._profile_top_songs_lock_for(tmp_path, f'A{i}')

    locks = artist_profile._top_songs_locks
    assert locks[key] is held
    assert len(locks) <= 2


# ── Downloader: per-output-path lock dict ──────────────────────────


def _target_key(dl, song: dict) -> str:
    return '/'.join(p.casefold() for p in dl._format_output_parts(song))


def test_downloader_target_locks_are_capped_and_drop_the_oldest(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(downloader_mod, '_MAX_TARGET_LOCKS', 3)
    dl = downloader_mod.Downloader(tmp_path)
    songs = [{'name': f'Track {i}', 'artists': ['Paramore']} for i in range(5)]
    for song in songs:
        dl._target_lock(song)

    locks = dl._target_locks
    assert len(locks) == 3
    assert _target_key(dl, songs[0]) not in locks
    assert _target_key(dl, songs[-1]) in locks


def test_downloader_target_lock_is_the_same_object_for_the_same_target(
    tmp_path,
):
    dl = downloader_mod.Downloader(tmp_path)
    song = {'name': 'Track', 'artists': ['Paramore']}
    assert dl._target_lock(song) is dl._target_lock(dict(song))
    assert len(dl._target_locks) == 1


# ── Spotify connect: abandoned OAuth states are purged ──────────────


@pytest.fixture(autouse=True)
def _clean_connect_states():
    api._spotify_connect_states.clear()
    yield
    api._spotify_connect_states.clear()


class _FakeRequest:
    base_url = 'http://testserver/'


def test_expired_connect_states_are_purged():
    now = time.time()
    api._spotify_connect_states['fresh'] = ('verifier', now + 300)
    api._spotify_connect_states['stale'] = ('verifier', now - 1)

    api._purge_spotify_connect_states(now)

    assert 'fresh' in api._spotify_connect_states
    assert 'stale' not in api._spotify_connect_states


def test_authorize_purges_abandoned_connect_states(monkeypatch):
    monkeypatch.setitem(
        api.state.settings, 'spotify_mirror', {'client_id': 'cid'}
    )
    monkeypatch.setattr(
        api.spotify_mirror, 'pkce_pair', lambda: ('verifier', 'challenge')
    )
    now = time.time()
    api._spotify_connect_states['abandoned'] = ('verifier', now - 1)

    response = asyncio.run(
        api.spotify_mirror_authorize_endpoint(_FakeRequest())
    )

    assert response.status_code == 302
    assert 'abandoned' not in api._spotify_connect_states
    assert len(api._spotify_connect_states) == 1
    state_value = next(iter(api._spotify_connect_states))
    verifier, expires_at = api._spotify_connect_states[state_value]
    assert verifier == 'verifier'
    assert expires_at > time.time()
    assert f'state={state_value}' in response.headers['location']
