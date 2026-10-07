"""Tests for last.fm scrobbling (downtify.scrobbling).

Every sender is injected, so nothing touches the network; the assertions
cover the signed call shape, the scrobble threshold, the auth flow and
the fire-and-forget contract (a failure returns falsy, never raises).
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from downtify import api, scrobbling


class FakeResponse:
    """Stand-in for an httpx response: ``status_code`` and a JSON body."""

    def __init__(self, body=None, status_code: int = 200) -> None:
        self._body = body if body is not None else {}
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f'HTTP {self.status_code}')

    def json(self):
        return self._body


def _sender(calls, body=None, status=200):
    def post(url, data, timeout):
        calls.append({'url': url, 'data': dict(data), 'timeout': timeout})
        return FakeResponse(body, status)

    return post


def _config(**overrides):
    config = {
        'api_key': 'abc',
        'api_secret': 'supersecret',
        'session_key': 'sk-123',
    }
    config.update(overrides)
    return config


def _settings(**overrides):
    block = {
        'enabled': True,
        'lastfm_enabled': True,
        'lastfm_api_key': 'abc',
        'lastfm_api_secret': 'supersecret',
        'lastfm_session_key': 'sk-123',
        'lastfm_username': 'someone',
        'scrobble_now_playing': True,
    }
    block.update(overrides)
    return {'scrobbling': block}


# ── signature ────────────────────────────────────────────────────────


def test_signature_matches_lastfm_rule():
    params = {'api_key': 'abc', 'method': 'auth.getToken', 'format': 'json'}
    assert (
        scrobbling._signature(params, 'supersecret')
        == '5b97ce5a3f28f08cc16aac134ad652f2'
    )


def test_signature_is_order_independent_and_skips_empties():
    a = {'artist': 'A', 'track': 'T', 'album': '', 'callback': 'x'}
    b = {'track': 'T', 'artist': 'A'}
    assert scrobbling._signature(a, 'sec') == scrobbling._signature(b, 'sec')


def test_signature_changes_with_a_value():
    a = scrobbling._signature({'artist': 'A'}, 'sec')
    b = scrobbling._signature({'artist': 'B'}, 'sec')
    assert a != b


# ── credentials / config ─────────────────────────────────────────────


def test_credentials_none_without_key_or_secret():
    assert scrobbling.lastfm_credentials({}) is None
    assert scrobbling.lastfm_credentials({'lastfm_api_key': 'a'}) is None
    assert scrobbling.lastfm_credentials(None) is None


def test_credentials_trim_and_keep_session():
    creds = scrobbling.lastfm_credentials({
        'lastfm_api_key': ' a ',
        'lastfm_api_secret': ' s ',
        'lastfm_session_key': ' k ',
    })
    assert creds == {
        'api_key': 'a',
        'api_secret': 's',
        'session_key': 'k',
    }


def test_active_config_requires_enabled_and_session():
    assert scrobbling.active_lastfm_config(_settings(enabled=False)) is None
    assert (
        scrobbling.active_lastfm_config(_settings(lastfm_enabled=False))
        is None
    )
    assert (
        scrobbling.active_lastfm_config(_settings(lastfm_session_key=''))
        is None
    )


def test_active_config_when_on():
    config = scrobbling.active_lastfm_config(_settings())
    assert config['session_key'] == 'sk-123'
    assert config['now_playing'] is True


# ── track mapping / threshold ────────────────────────────────────────


def test_track_params_basic():
    params = scrobbling.track_params({'artist': 'A', 'title': 'T'})
    assert params == {'artist': 'A', 'track': 'T'}


def test_track_params_include_album_and_duration():
    params = scrobbling.track_params({
        'artist': 'A',
        'title': 'T',
        'album': 'Al',
        'duration': 210.4,
    })
    assert params == {
        'artist': 'A',
        'track': 'T',
        'album': 'Al',
        'duration': '210',
    }


def test_track_params_none_when_unnamed():
    assert scrobbling.track_params({'artist': 'A'}) is None
    assert scrobbling.track_params({'title': 'T'}) is None
    assert scrobbling.track_params('nope') is None


def test_threshold_zero_for_short_tracks():
    assert scrobbling.scrobble_threshold(29) == 0.0
    assert scrobbling.scrobble_threshold(0) == 0.0
    assert scrobbling.scrobble_threshold('x') == 0.0


def test_threshold_half_or_four_minutes():
    assert scrobbling.scrobble_threshold(100) == 50.0
    assert scrobbling.scrobble_threshold(600) == 240.0


def test_is_scrobbleable_at_the_threshold():
    track = {'duration': 200}
    assert scrobbling.is_scrobbleable(track, 99) is False
    assert scrobbling.is_scrobbleable(track, 100) is True
    assert scrobbling.is_scrobbleable({'duration': 10}, 10) is False


# ── sending ──────────────────────────────────────────────────────────


def test_update_now_playing_posts_signed():
    calls = []
    ok = scrobbling.update_now_playing(
        {'artist': 'A', 'title': 'T'},
        _config(),
        post=_sender(calls, {'nowplaying': {'artist': 'A'}}),
    )
    assert ok is True
    data = calls[0]['data']
    assert calls[0]['url'] == scrobbling.LASTFM_API
    assert data['method'] == 'track.updateNowPlaying'
    assert data['artist'] == 'A'
    assert data['sk'] == 'sk-123'
    assert data['api_sig'] == scrobbling._signature(
        {k: v for k, v in data.items() if k != 'api_sig'}, 'supersecret'
    )


def test_update_now_playing_false_when_unnamed():
    calls = []
    assert (
        scrobbling.update_now_playing(
            {'artist': 'A'}, _config(), post=_sender(calls)
        )
        is False
    )
    assert calls == []


def test_scrobble_posts_timestamp():
    calls = []
    ok = scrobbling.scrobble(
        {'artist': 'A', 'title': 'T'},
        _config(),
        timestamp=1700000000,
        post=_sender(calls, {'scrobbles': {'@attr': {'accepted': 1}}}),
    )
    assert ok is True
    assert calls[0]['data']['method'] == 'track.scrobble'
    assert calls[0]['data']['timestamp'] == '1700000000'


def test_call_returns_empty_on_http_error():
    calls = []
    assert (
        scrobbling.scrobble(
            {'artist': 'A', 'title': 'T'},
            _config(),
            post=_sender(calls, status=500),
        )
        is False
    )


def test_call_returns_empty_on_exception():
    def boom(url, data, timeout):
        raise OSError('no network')

    assert (
        scrobbling.scrobble(
            {'artist': 'A', 'title': 'T'}, _config(), post=boom
        )
        is False
    )


# ── auth flow ────────────────────────────────────────────────────────


def test_get_token_returns_token():
    calls = []
    token = scrobbling.get_token(
        _config(), post=_sender(calls, {'token': 'req-token'})
    )
    assert token == 'req-token'


def test_get_token_none_on_failure():
    assert (
        scrobbling.get_token(_config(), post=_sender([], status=403)) is None
    )


def test_get_session_returns_key_and_username():
    body = {'session': {'key': 'sess', 'name': 'listener'}}
    session = scrobbling.get_session(
        _config(), 'req-token', post=_sender([], body)
    )
    assert session == {'session_key': 'sess', 'username': 'listener'}


def test_get_session_none_without_key():
    assert (
        scrobbling.get_session(
            _config(), 't', post=_sender([], {'session': {'name': 'x'}})
        )
        is None
    )


def test_build_auth_url():
    url = scrobbling.build_auth_url('abc', 'tok')
    assert url == 'https://www.last.fm/api/auth/?api_key=abc&token=tok'


def test_test_connection_ok():
    body = {'user': {'name': 'listener'}}
    result = scrobbling.check_connection(_config(), post=_sender([], body))
    assert result == {'ok': True, 'username': 'listener'}


def test_test_connection_missing_credentials():
    assert scrobbling.check_connection({}) == {
        'ok': False,
        'error': 'missing_credentials',
    }


def test_test_connection_auth_failed():
    assert scrobbling.check_connection(
        _config(), post=_sender([], {'error': 9})
    ) == {'ok': False, 'error': 'auth_failed'}


# ── tracker ──────────────────────────────────────────────────────────


def test_tracker_now_playing_once_per_song():
    tracker = scrobbling.ScrobbleTracker()
    assert tracker.should_send_now_playing(1, 'p', 'song') is True
    assert tracker.should_send_now_playing(1, 'p', 'song') is False
    assert tracker.should_send_now_playing(1, 'p', 'other') is True


def test_tracker_scrobble_once_per_song():
    tracker = scrobbling.ScrobbleTracker()
    assert tracker.should_scrobble(1, 'p', 'song') is True
    assert tracker.should_scrobble(1, 'p', 'song') is False


def test_tracker_forget_user():
    tracker = scrobbling.ScrobbleTracker()
    tracker.should_scrobble(1, 'p', 'song')
    tracker.forget_user(1)
    assert tracker.should_scrobble(1, 'p', 'song') is True


# ── settings plumbing ────────────────────────────────────────────────


def test_defaults_present_and_off():
    block = api.DEFAULT_SETTINGS['scrobbling']
    assert block['enabled'] is False
    assert block['lastfm_enabled'] is False
    assert block['scrobble_now_playing'] is True


def test_scrobbling_is_a_nested_setting():
    assert 'scrobbling' in api._NESTED_SETTINGS


def test_clean_coerces_and_fills():
    cleaned = api._clean_scrobbling({
        'enabled': 1,
        'lastfm_api_key': '  a  ',
    })
    assert cleaned == {
        'enabled': True,
        'lastfm_enabled': False,
        'lastfm_api_key': 'a',
        'lastfm_api_secret': '',
        'lastfm_session_key': '',
        'lastfm_username': '',
        'scrobble_now_playing': True,
    }


def test_validate_rejects_enabled_without_credentials():
    with pytest.raises(HTTPException):
        api._validate_scrobbling_settings({
            'enabled': True,
            'lastfm_enabled': True,
            'lastfm_api_key': '',
            'lastfm_api_secret': '',
        })


def test_validate_rejects_enabled_without_session():
    with pytest.raises(HTTPException):
        api._validate_scrobbling_settings({
            'enabled': True,
            'lastfm_enabled': True,
            'lastfm_api_key': 'a',
            'lastfm_api_secret': 's',
            'lastfm_session_key': '',
        })


def test_validate_accepts_complete_config():
    api._validate_scrobbling_settings({
        'enabled': True,
        'lastfm_enabled': True,
        'lastfm_api_key': 'a',
        'lastfm_api_secret': 's',
        'lastfm_session_key': 'k',
    })


def test_validate_skips_when_not_enabled():
    api._validate_scrobbling_settings({'enabled': False})
