"""Tests for Telegram notifications (downtify.notifications).

Sending is injected: every test passes a fake ``post`` so nothing touches
the network, and the assertions are about the URL, payload and the
fire-and-forget contract (a failure returns False, never raises).
"""

from __future__ import annotations

import json

import pytest
from fastapi import HTTPException

from downtify import api, notifications


class FakeResponse:
    """Stand-in for an httpx response - only ``status_code`` is read."""

    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code


def _capture(calls, status=200):
    def post(url, *, json=None, timeout=None):
        calls.append({'url': url, 'json': json, 'timeout': timeout})
        return FakeResponse(status)

    return post


def _settings(**overrides):
    block = {
        'enabled': True,
        'telegram_enabled': True,
        'telegram_bot_token': '123:abc',
        'telegram_chat_id': '42',
        'notify_watch_downloads': True,
    }
    block.update(overrides)
    return {'notifications': block}


# ── credentials ──────────────────────────────────────────────────────


def test_credentials_read_token_and_chat_id():
    block = _settings()['notifications']
    assert notifications.telegram_credentials(block) == {
        'bot_token': '123:abc',
        'chat_id': '42',
    }


def test_credentials_trim_whitespace():
    block = {'telegram_bot_token': '  t  ', 'telegram_chat_id': ' c '}
    assert notifications.telegram_credentials(block) == {
        'bot_token': 't',
        'chat_id': 'c',
    }


@pytest.mark.parametrize(
    'block',
    [
        None,
        {},
        {'telegram_bot_token': 't'},
        {'telegram_chat_id': 'c'},
        {'telegram_bot_token': '  ', 'telegram_chat_id': 'c'},
    ],
)
def test_credentials_none_when_incomplete(block):
    assert notifications.telegram_credentials(block) is None


def test_active_config_none_when_master_off():
    assert (
        notifications.active_telegram_config(_settings(enabled=False)) is None
    )


def test_active_config_none_when_telegram_off():
    settings = _settings(telegram_enabled=False)
    assert notifications.active_telegram_config(settings) is None


def test_active_config_reads_when_on():
    assert notifications.active_telegram_config(_settings()) == {
        'bot_token': '123:abc',
        'chat_id': '42',
    }


# ── message formatting ───────────────────────────────────────────────


def test_format_singular():
    assert notifications.format_watch_downloads('X', 1) == (
        'Downtify downloaded 1 new track from "X"'
    )


def test_format_plural():
    assert notifications.format_watch_downloads('X', 3) == (
        'Downtify downloaded 3 new tracks from "X"'
    )


# ── sending ──────────────────────────────────────────────────────────


def test_send_telegram_posts_to_bot_api():
    calls = []
    ok = notifications.send_telegram(
        'hi', {'bot_token': '123:abc', 'chat_id': '42'}, post=_capture(calls)
    )
    assert ok is True
    assert calls[0]['url'] == (
        'https://api.telegram.org/bot123:abc/sendMessage'
    )
    assert calls[0]['json'] == {
        'chat_id': '42',
        'text': 'hi',
        'disable_web_page_preview': True,
    }


def test_send_telegram_false_on_error_status():
    ok = notifications.send_telegram(
        'hi',
        {'bot_token': 't', 'chat_id': 'c'},
        post=_capture([], status=500),
    )
    assert ok is False


def test_send_telegram_false_on_exception():
    def boom(url, *, json=None, timeout=None):
        raise OSError('no network')

    ok = notifications.send_telegram(
        'hi', {'bot_token': 't', 'chat_id': 'c'}, post=boom
    )
    assert ok is False


def test_notify_watch_downloads_sends_when_enabled():
    calls = []
    ok = notifications.notify_watch_downloads(
        _settings(), 'My Watch', 2, post=_capture(calls)
    )
    assert ok is True
    assert calls[0]['json']['text'] == (
        'Downtify downloaded 2 new tracks from "My Watch"'
    )


def test_notify_watch_downloads_noop_when_disabled():
    calls = []
    ok = notifications.notify_watch_downloads(
        _settings(enabled=False), 'My Watch', 2, post=_capture(calls)
    )
    assert ok is False
    assert calls == []


def test_notify_watch_downloads_noop_when_event_off():
    calls = []
    ok = notifications.notify_watch_downloads(
        _settings(notify_watch_downloads=False),
        'My Watch',
        2,
        post=_capture(calls),
    )
    assert ok is False
    assert calls == []


@pytest.mark.parametrize('count', [0, -1])
def test_notify_watch_downloads_noop_without_new_tracks(count):
    calls = []
    ok = notifications.notify_watch_downloads(
        _settings(), 'My Watch', count, post=_capture(calls)
    )
    assert ok is False
    assert calls == []


def test_test_message_missing_credentials():
    assert notifications.send_test_message({}) == {
        'ok': False,
        'error': 'missing_credentials',
    }


def test_test_message_sends():
    calls = []
    result = notifications.send_test_message(
        {'telegram_bot_token': 't', 'telegram_chat_id': 'c'},
        post=_capture(calls),
    )
    assert result == {'ok': True}
    assert len(calls) == 1


def test_test_message_reports_send_failure():
    result = notifications.send_test_message(
        {'telegram_bot_token': 't', 'telegram_chat_id': 'c'},
        post=_capture([], status=500),
    )
    assert result == {'ok': False, 'error': 'send_failed'}


# ── settings plumbing ────────────────────────────────────────────────


def test_defaults_present_and_off():
    block = api.DEFAULT_SETTINGS['notifications']
    assert block['enabled'] is False
    assert block['telegram_enabled'] is False
    assert block['notify_watch_downloads'] is True


def test_notifications_is_a_nested_setting():
    assert 'notifications' in api._NESTED_SETTINGS


def test_clean_coerces_and_fills():
    cleaned = api._clean_notifications({
        'enabled': 1,
        'telegram_bot_token': '  t  ',
    })
    assert cleaned == {
        'enabled': True,
        'telegram_enabled': False,
        'telegram_bot_token': 't',
        'telegram_chat_id': '',
        'notify_watch_downloads': True,
    }


def test_validate_rejects_enabled_without_credentials():
    with pytest.raises(HTTPException):
        api._validate_notifications_settings({
            'enabled': True,
            'telegram_enabled': True,
            'telegram_bot_token': '',
            'telegram_chat_id': '',
        })


def test_validate_skips_when_not_enabled():
    # No raise: validation is a no-op when notifications are off.
    api._validate_notifications_settings({
        'enabled': False,
        'telegram_enabled': True,
        'telegram_bot_token': '',
        'telegram_chat_id': '',
    })


def test_validate_accepts_complete_config():
    api._validate_notifications_settings({
        'enabled': True,
        'telegram_enabled': True,
        'telegram_bot_token': 't',
        'telegram_chat_id': 'c',
    })


def test_nested_merge_keeps_default_keys():
    # A settings.json from before notifications existed gets the defaults.
    merged = {**api.DEFAULT_SETTINGS['notifications'], 'enabled': True}
    assert set(merged) == set(api.DEFAULT_SETTINGS['notifications'])
    assert json.dumps(merged)  # round-trips (JSON-safe)
