"""Tests for the Spotify Mirror (downtify.spotify_mirror).

Every HTTP call is injected, so nothing touches the network; the
assertions are about the request shapes (PKCE, token exchange, the
play command), the dedupe contract and the fire-and-forget policy.
"""

from __future__ import annotations

import base64
import hashlib
import time

import pytest
from fastapi import HTTPException

from downtify import api, spotify_mirror


class FakeResponse:
    def __init__(self, body=None, status_code: int = 200) -> None:
        self._body = body if body is not None else {}
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f'HTTP {self.status_code}')

    def json(self):
        return self._body


def _request(calls, body=None, status=200):
    def request(  # noqa: PLR0913, PLR0917
        method, url, *, headers=None, params=None, json=None, data=None
    ):
        calls.append({
            'method': method,
            'url': url,
            'headers': headers or {},
            'params': params or {},
            'json': json,
            'data': data,
        })
        return FakeResponse(body, status)

    return request


def _config(**overrides):
    config = {
        'client_id': 'cid',
        'access_token': 'at',
        'refresh_token': 'rt',
        'device_id': 'dev-1',
        'token_expires_at': 0,
        'silent_on_target': True,
    }
    config.update(overrides)
    return config


def _settings(**overrides):
    block = {
        'enabled': True,
        'client_id': 'cid',
        'device_id': 'dev-1',
        'access_token': 'at',
        'refresh_token': 'rt',
        'token_expires_at': 0,
        'silent_on_target': True,
    }
    block.update(overrides)
    return {'spotify_mirror': block}


# ── PKCE + authorize ─────────────────────────────────────────────────


def test_pkce_pair_follows_rfc7636():
    verifier, challenge = spotify_mirror.pkce_pair()
    assert 43 <= len(verifier) <= 128
    expected = (
        base64
        .urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .decode()
        .rstrip('=')
    )
    assert challenge == expected
    assert '=' not in verifier
    assert '=' not in challenge


def test_authorize_url_encodes_everything():
    url = spotify_mirror.authorize_url('cid', 'http://srv/cb', 'STATE', 'CH')

    assert url.startswith(spotify_mirror.SPOTIFY_ACCOUNTS + '/authorize?')
    assert 'client_id=cid' in url
    assert 'response_type=code' in url
    assert 'redirect_uri=http%3A%2F%2Fsrv%2Fcb' in url
    assert 'code_challenge_method=S256' in url
    assert 'scope=' in url
    assert 'user-modify-playback-state' in url


# ── token exchange / refresh ─────────────────────────────────────────


def test_exchange_code_posts_pkce_fields():
    calls = []
    tokens = spotify_mirror.exchange_code(
        'cid',
        'CODE',
        'http://srv/cb',
        'VERIFIER',
        request=_request(
            calls,
            {
                'access_token': 'at2',
                'refresh_token': 'rt2',
                'expires_in': 3600,
            },
        ),
    )

    assert tokens['access_token'] == 'at2'
    assert tokens['refresh_token'] == 'rt2'
    assert tokens['token_expires_at'] > 0
    data = calls[0]['data']
    assert data['grant_type'] == 'authorization_code'
    assert data['code'] == 'CODE'
    assert data['code_verifier'] == 'VERIFIER'
    assert data['client_id'] == 'cid'


def test_exchange_code_none_on_http_error():
    tokens = spotify_mirror.exchange_code(
        'cid', 'c', 'http://srv/cb', 'v', request=_request([], status=400)
    )
    assert tokens is None


def test_refresh_keeps_the_old_token_when_none_returned():
    calls = []
    tokens = spotify_mirror.refresh_access_token(
        'cid', 'rt-old', request=_request(calls, {'access_token': 'at3'})
    )

    assert tokens['access_token'] == 'at3'
    # Spotify repeats refresh_token on rotation; keep the known one.
    assert tokens['refresh_token'] == 'rt-old'
    assert calls[0]['data']['grant_type'] == 'refresh_token'


def test_ensure_token_passes_fresh_through():
    config = _config(token_expires_at=time.time() + 3600)
    calls = []
    assert (
        spotify_mirror.ensure_token(config, request=_request(calls)) == config
    )
    assert calls == []


def test_ensure_token_refreshes_when_stale():
    calls = []
    config = _config(token_expires_at=0)
    renewed = spotify_mirror.ensure_token(
        config, request=_request(calls, {'access_token': 'at-new'})
    )

    assert renewed['access_token'] == 'at-new'
    assert renewed['refresh_token'] == 'rt'


def test_ensure_token_none_without_refresh_token():
    config = _config(token_expires_at=0, refresh_token='')
    assert spotify_mirror.ensure_token(config, request=_request([])) is None


# ── credentials / active config ──────────────────────────────────────


def test_credentials_none_without_client_id():
    assert spotify_mirror.mirror_credentials({}) is None
    assert spotify_mirror.mirror_credentials(None) is None


def test_active_config_requires_enabled_device_and_token():
    assert (
        spotify_mirror.active_mirror_config(_settings(enabled=False)) is None
    )
    assert spotify_mirror.active_mirror_config(_settings(device_id='')) is None
    assert (
        spotify_mirror.active_mirror_config(
            _settings(access_token='', refresh_token='')
        )
        is None
    )


def test_active_config_when_ready():
    config = spotify_mirror.active_mirror_config(_settings())
    assert config['device_id'] == 'dev-1'
    assert config['silent_on_target'] is True


# ── devices / play ───────────────────────────────────────────────────


def test_list_devices_returns_normalized_rows():
    calls = []
    devices = spotify_mirror.list_devices(
        _config(token_expires_at=99999999999),
        request=_request(
            calls,
            {
                'devices': [
                    {
                        'id': 'd1',
                        'name': 'Downtify Mirror',
                        'is_active': False,
                    },
                    {'id': '', 'name': 'broken'},  # no id → dropped
                ]
            },
        ),
    )

    assert devices == [
        {'id': 'd1', 'name': 'Downtify Mirror', 'is_active': False}
    ]
    assert calls[0]['headers']['Authorization'] == 'Bearer at'


def test_list_devices_empty_when_token_cannot_renew():
    devices = spotify_mirror.list_devices(
        _config(token_expires_at=0, refresh_token=''), request=_request([])
    )
    assert devices == []


def test_play_track_puts_play_on_the_device():
    calls = []
    ok = spotify_mirror.play_track(
        _config(token_expires_at=99999999999),
        'spotify:track:ID',
        request=_request(calls, status=204),
    )

    assert ok is True
    play = [
        c for c in calls if c['method'] == 'PUT' and 'player/play' in c['url']
    ][0]
    assert play['params'] == {'device_id': 'dev-1'}
    assert play['json'] == {'uris': ['spotify:track:ID']}
    # silent default: a volume command goes out before the play
    volume = [c for c in calls if 'volume' in c['url']]
    assert volume
    assert volume[0]['params']['volume_percent'] == 0


def test_play_track_loud_when_not_silent():
    calls = []
    ok = spotify_mirror.play_track(
        _config(token_expires_at=99999999999, silent_on_target=False),
        'spotify:track:ID',
        silent=False,
        request=_request(calls, status=204),
    )

    assert ok is True
    assert not [c for c in calls if 'volume' in c['url']]


def test_play_track_false_on_http_error():
    ok = spotify_mirror.play_track(
        _config(token_expires_at=99999999999),
        'spotify:track:ID',
        request=_request([], status=403),
    )
    assert ok is False


# ── uri resolution ───────────────────────────────────────────────────


class _Index:
    def __init__(self, mapping) -> None:
        self._mapping = mapping

    def spotify_id_for_filename(self, filename):
        return self._mapping.get(filename)


class _Library:
    def __init__(self, index) -> None:
        self.track_index = index


def test_uri_from_the_track_index():
    library = _Library(_Index({'Road Trip/Alpha.mp3': 'S' * 22}))
    uri = spotify_mirror.uri_for_track(
        _config(),
        {'file': 'Road Trip/Alpha.mp3', 'artist': 'A', 'title': 'T'},
        library=library,
        request=_request([]),
    )
    assert uri == f'spotify:track:{"S" * 22}'


def test_uri_falls_back_to_search():
    calls = []
    library = _Library(_Index({}))
    uri = spotify_mirror.uri_for_track(
        _config(token_expires_at=99999999999),
        {'file': 'X.mp3', 'artist': 'Artist', 'title': 'Title'},
        library=library,
        request=_request(
            calls,
            {
                'tracks': {
                    'items': [
                        {'uri': 'spotify:track:Z' * 1},
                    ]
                }
            },
        ),
    )

    assert uri == 'spotify:track:Z'
    assert calls[0]['params']['type'] == 'track'
    assert 'Artist' in calls[0]['params']['q']
    assert 'Title' in calls[0]['params']['q']


def test_uri_none_when_unnamed_and_index_empty():
    uri = spotify_mirror.uri_for_track(
        _config(),
        {'file': 'X.mp3', 'artist': '', 'title': ''},
        library=_Library(_Index({})),
        request=_request([]),
    )
    assert uri is None


# ── mirror_track ─────────────────────────────────────────────────────


def test_mirror_track_reports_renewed_tokens():
    calls = []
    config = _config(token_expires_at=0)  # stale → refresh happens

    def request(  # noqa: PLR0913, PLR0917
        method, url, *, headers=None, params=None, json=None, data=None
    ):
        calls.append(method + ' ' + url)
        if 'api/token' in url:
            return FakeResponse(
                {'access_token': 'at-new', 'expires_in': 3600}, 200
            )
        if '/search' in url:
            return FakeResponse(
                {'tracks': {'items': [{'uri': 'spotify:track:AAAAA'}]}}, 200
            )
        return FakeResponse({}, 204)

    result = spotify_mirror.mirror_track(
        config,
        {'file': 'X.mp3', 'artist': 'A', 'title': 'T'},
        request=request,
    )

    # The caller is told to persist the renewed token.
    assert result['access_token'] == 'at-new'


def test_mirror_track_none_when_no_uri_found():
    result = spotify_mirror.mirror_track(
        _config(),
        {'file': 'X.mp3', 'artist': '', 'title': ''},
        library=_Library(_Index({})),
        request=_request([]),
    )
    assert result is None


# ── test_connection ──────────────────────────────────────────────────


def test_verify_connection_ok_with_device():
    calls = []
    result = spotify_mirror.verify_connection(
        _config(token_expires_at=99999999999),
        request=_request(calls, {'display_name': 'listener'}),
    )
    # /me answered; the device list is the follow-up call.
    assert result == {
        'ok': False,
        'error': 'device_missing',
        'username': 'listener',
    }


def test_verify_connection_ok_with_full_flow():
    responses = {
        '/me': FakeResponse({'display_name': 'listener'}, 200),
        '/me/player/devices': FakeResponse(
            {'devices': [{'id': 'dev-1', 'name': 'Downtify Mirror'}]}, 200
        ),
    }

    def request(method, url, **_):
        for path, response in responses.items():
            if url.endswith(path):
                return response
        return FakeResponse({}, 200)

    result = spotify_mirror.verify_connection(
        _config(token_expires_at=99999999999), request=request
    )
    assert result == {
        'ok': True,
        'username': 'listener',
        'device': 'Downtify Mirror',
    }


def test_verify_connection_auth_failed():
    result = spotify_mirror.verify_connection(
        _config(token_expires_at=0, refresh_token=''), request=_request([])
    )
    assert result == {'ok': False, 'error': 'auth_failed'}


# ── tracker ──────────────────────────────────────────────────────────


def test_tracker_mirrors_once_per_song():
    tracker = spotify_mirror.MirrorTracker()
    assert tracker.should_mirror(1, 'p', 'song') is True
    assert tracker.should_mirror(1, 'p', 'song') is False
    assert tracker.should_mirror(1, 'p', 'other') is True
    tracker.forget_user(1)
    assert tracker.should_mirror(1, 'p', 'song') is True


# ── settings plumbing ────────────────────────────────────────────────


def test_defaults_present_and_off():
    block = api.DEFAULT_SETTINGS['spotify_mirror']
    assert block['enabled'] is False
    assert block['silent_on_target'] is True


def test_spotify_mirror_is_a_nested_setting():
    assert 'spotify_mirror' in api._NESTED_SETTINGS


def test_clean_coerces_and_fills():
    cleaned = api._clean_spotify_mirror({
        'enabled': 1,
        'client_id': '  cid  ',
    })
    assert cleaned == {
        'enabled': True,
        'client_id': 'cid',
        'redirect_uri': '',
        'device_id': '',
        'access_token': '',
        'refresh_token': '',
        'token_expires_at': '',
        'mirror_user': '',
        'silent_on_target': True,
        'mirror_manual_checks': False,
    }


def test_validate_rejects_enabled_without_client_id():
    with pytest.raises(HTTPException):
        api._validate_spotify_mirror_settings({
            'enabled': True,
            'client_id': '',
            'device_id': 'd',
        })


def test_validate_allows_enabled_without_device_before_connecting():
    """The connect flow saves first: tokens and the device come later.

    A block with just the client id is valid - the runtime hooks keep
    it inert until both exist.
    """

    api._validate_spotify_mirror_settings({
        'enabled': True,
        'client_id': 'c',
        'device_id': '',
        'refresh_token': '',
    })


def test_validate_accepts_complete_config():
    api._validate_spotify_mirror_settings({
        'enabled': True,
        'client_id': 'c',
        'device_id': 'd',
        'refresh_token': 'r',
    })


def test_validate_skips_when_not_enabled():
    api._validate_spotify_mirror_settings({'enabled': False})


# -- transport commands (pause / resume / seek) -----------------------


def test_pause_playback_puts_pause_on_the_device():
    calls = []
    ok = spotify_mirror.pause_playback(
        _config(token_expires_at=99999999999),
        request=_request(calls, status=204),
    )

    assert ok is True
    assert calls[0]['url'].endswith('/me/player/pause')
    assert calls[0]['params'] == {'device_id': 'dev-1'}


def test_resume_playback_puts_play_without_a_body():
    calls = []
    ok = spotify_mirror.resume_playback(
        _config(token_expires_at=99999999999),
        request=_request(calls, status=204),
    )

    assert ok is True
    assert calls[0]['url'].endswith('/me/player/play')
    assert calls[0]['json'] is None


def test_seek_playback_converts_seconds_to_milliseconds():
    calls = []
    ok = spotify_mirror.seek_playback(
        _config(token_expires_at=99999999999),
        12.5,
        request=_request(calls, status=204),
    )

    assert ok is True
    assert calls[0]['url'].endswith('/me/player/seek')
    assert calls[0]['params']['position_ms'] == 12500


def test_seek_playback_false_for_an_unreadable_position():
    assert (
        spotify_mirror.seek_playback(_config(), 'abc', request=_request([]))
        is False
    )


def test_transport_false_without_a_device():
    assert (
        spotify_mirror.pause_playback(
            _config(token_expires_at=99999999999, device_id=''),
            request=_request([]),
        )
        is False
    )


# -- tracker transitions ----------------------------------------------


def test_tracker_pauses_and_resumes_once():
    tracker = spotify_mirror.MirrorTracker()
    assert tracker.should_mirror(1, 'p', 'song') is True
    assert tracker.should_pause(1, 'p', 'song') is True
    assert tracker.should_pause(1, 'p', 'song') is False
    assert tracker.should_resume(1, 'p', 'song') is True
    assert tracker.should_resume(1, 'p', 'song') is False


def test_tracker_ignores_pause_for_an_unmirrored_song():
    tracker = spotify_mirror.MirrorTracker()
    tracker.should_mirror(1, 'p', 'song')
    assert tracker.should_pause(1, 'p', 'other') is False


def test_tracker_pause_any_after_a_stop():
    tracker = spotify_mirror.MirrorTracker()
    tracker.should_mirror(1, 'p', 'song')
    assert tracker.should_pause_any(1, 'p') is True
    assert tracker.should_pause_any(1, 'p') is False


def test_tracker_knows_only_the_current_song():
    tracker = spotify_mirror.MirrorTracker()
    tracker.should_mirror(1, 'p', 'song')
    assert tracker.knows(1, 'p', 'song') is True
    assert tracker.knows(1, 'p', 'other') is False


def test_tracker_a_new_song_resets_the_paused_state():
    tracker = spotify_mirror.MirrorTracker()
    tracker.should_mirror(1, 'p', 'one')
    tracker.should_pause(1, 'p', 'one')
    tracker.should_mirror(1, 'p', 'two')
    assert tracker.should_pause(1, 'p', 'two') is True


# -- end-of-track detection -------------------------------------------


def test_track_end_when_the_position_reaches_the_duration():
    assert spotify_mirror.is_track_end({'duration': 100}, 99.5) is True
    assert spotify_mirror.is_track_end({'duration': 100}, 100) is True
    assert spotify_mirror.is_track_end({'duration': 100}, 120) is True


def test_not_track_end_midway_or_without_duration():
    assert spotify_mirror.is_track_end({'duration': 100}, 50) is False
    assert spotify_mirror.is_track_end({'duration': 0}, 50) is False
    assert spotify_mirror.is_track_end({}, 50) is False
    assert spotify_mirror.is_track_end(None, 50) is False
