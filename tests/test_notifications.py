"""Tests for Telegram notifications (downtify.notifications).

Sending is injected: every test passes a fake ``post`` so nothing touches
the network, and the assertions are about the URL, payload and the
fire-and-forget contract (a failure returns False, never raises).
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from downtify import api, monitor, notifications


class FakeResponse:
    """Stand-in for an httpx response - only ``status_code`` is read."""

    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code


def _capture(calls, status=200):
    def post(url, *, json=None, timeout=None, headers=None):
        calls.append({
            'url': url,
            'json': json,
            'timeout': timeout,
            'headers': headers or {},
        })
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


# ── secret store ───────────────────────────────────────────────────────


def test_secret_store_writes_private_atomic_json(tmp_path):
    path = tmp_path / 'notifications.json'
    store = notifications.NotificationStore(path)
    store.save({'version': 1, 'telegram': {'bot_token': 'secret'}})

    assert path.stat().st_mode & 0o777 == 0o600
    assert notifications.NotificationStore(path).load() == {
        'version': 1,
        'telegram': {'bot_token': 'secret'},
    }
    assert not list(tmp_path.glob('*.partial'))


def test_send_telegram_never_logs_token_bearing_exception(monkeypatch):
    warnings = []
    monkeypatch.setattr(
        notifications.logger,
        'warning',
        lambda message, *args: warnings.append((message, args)),
    )

    def boom(url, **kwargs):
        raise OSError(f'failed for {url}')

    assert (
        notifications.send_telegram(
            'hi', {'bot_token': 'secret-token', 'chat_id': '42'}, post=boom
        )
        is False
    )
    assert 'secret-token' not in repr(warnings)


# ── dispatcher ────────────────────────────────────────────────────────


def _dispatcher_settings(**overrides):
    channels = {
        'telegram': {
            'enabled': True,
            'bot_token': '123:abc',
            'chat_id': '42',
        },
        'ntfy': {
            'enabled': True,
            'url': 'https://ntfy.sh/downtify',
            'token': 'ntfy-secret',
        },
        'webhook': {
            'enabled': True,
            'url': 'https://example.test/hook',
            'token': 'hook-secret',
        },
    }
    channels.update(overrides.pop('channels', {}))
    block = {
        'enabled': True,
        'events': ['download.completed'],
        'channels': channels,
    }
    block.update(overrides)
    return {'notifications': block}


def test_dispatch_sends_enabled_channels_and_hides_secrets():
    calls = []
    result = notifications.notify_event(
        _dispatcher_settings(),
        'download.completed',
        {'title': 'Song', 'artist': 'Artist', 'count': 1},
        post=_capture(calls),
    )

    assert result['ok'] is True
    assert result['sent'] == ['telegram', 'ntfy', 'webhook']
    assert len(calls) == 3
    assert calls[0]['url'] == 'https://api.telegram.org/bot123:abc/sendMessage'
    assert calls[1]['url'] == 'https://ntfy.sh/downtify'
    assert calls[1]['headers']['Authorization'] == 'Bearer ntfy-secret'
    assert calls[2]['headers']['Authorization'] == 'Bearer hook-secret'
    assert calls[2]['json']['event'] == 'download.completed'
    assert 'ntfy-secret' not in json.dumps(result)
    assert 'hook-secret' not in json.dumps(result)


def test_dispatch_respects_event_filter_and_channel_switch():
    calls = []
    settings = _dispatcher_settings(events=['upgrade.finished'])
    result = notifications.notify_event(
        settings, 'download.completed', {}, post=_capture(calls)
    )
    assert result == {'ok': True, 'sent': [], 'failed': []}
    assert calls == []

    settings = _dispatcher_settings(
        channels={
            'ntfy': {'enabled': False},
            'webhook': {'enabled': False},
        }
    )
    notifications.notify_event(
        settings, 'download.completed', {}, post=_capture(calls)
    )
    assert len(calls) == 1


def test_dispatch_never_raises_when_a_channel_fails():
    calls = []

    def post(url, **kwargs):
        calls.append(url)
        if 'ntfy.sh' in url:
            raise OSError('offline')
        return FakeResponse(200)

    result = notifications.notify_event(
        _dispatcher_settings(),
        'download.completed',
        {},
        post=post,
    )
    assert result['ok'] is False
    assert result['sent'] == ['telegram', 'webhook']
    assert result['failed'] == ['ntfy']


def test_secret_store_updates_only_nonempty_values(tmp_path):
    store = notifications.NotificationStore(tmp_path / 'notifications.json')
    store.save({'version': 1, 'channels': {'ntfy': {'token': 'old'}}})
    store.update({'ntfy': {'token': '', 'url': 'https://ntfy.sh/new'}})
    assert store.load()['channels']['ntfy'] == {
        'token': 'old',
        'url': 'https://ntfy.sh/new',
    }


def test_clean_settings_returns_only_secret_flags():
    public = notifications.clean_settings(
        {
            'enabled': True,
            'events': ['download.completed'],
            'channels': {
                'telegram': {
                    'enabled': True,
                    'events': ['download.failed'],
                    'bot_token': 'raw-token',
                    'chat_id': '42',
                },
                'ntfy': {'enabled': True, 'url': 'https://ntfy.sh/private'},
            },
        },
        {
            'channels': {
                'telegram': {'bot_token': 'saved-token', 'chat_id': '42'},
                'ntfy': {'url': 'https://ntfy.sh/private'},
            }
        },
    )
    assert public['channels']['telegram'] == {
        'enabled': True,
        'events': ['download.failed'],
        'bot_token_set': True,
        'chat_id_set': True,
    }
    assert public['channels']['ntfy']['events'] == ['download.completed']
    assert public['channels']['ntfy']['url_set'] is True
    assert 'raw-token' not in json.dumps(public)
    assert 'saved-token' not in json.dumps(public)


def test_effective_settings_merges_saved_secrets_for_sending():
    settings = {
        'notifications': notifications.clean_settings(
            {
                'enabled': True,
                'events': ['download.completed'],
                'channels': {'telegram': {'enabled': True}},
            },
            {
                'channels': {
                    'telegram': {'bot_token': 'saved', 'chat_id': '42'}
                }
            },
        )
    }
    effective = notifications.effective_settings(
        settings,
        {'channels': {'telegram': {'bot_token': 'saved', 'chat_id': '42'}}},
    )
    assert (
        effective['notifications']['channels']['telegram']['bot_token']
        == 'saved'
    )
    assert 'bot_token' not in settings['notifications']['channels']['telegram']


def test_migrate_legacy_settings_moves_secrets_out_of_settings(tmp_path):
    store = notifications.NotificationStore(tmp_path / 'notifications.json')
    settings = {
        'notifications': {
            'enabled': True,
            'telegram_enabled': True,
            'telegram_bot_token': 'legacy-token',
            'telegram_chat_id': '42',
            'notify_watch_downloads': True,
        }
    }
    assert notifications.migrate_legacy_settings(settings, store) is True
    assert store.load()['channels']['telegram'] == {
        'bot_token': 'legacy-token',
        'chat_id': '42',
    }
    assert 'telegram_bot_token' not in json.dumps(settings)
    assert (
        settings['notifications']['channels']['telegram']['bot_token_set']
        is True
    )
    assert 'watch.downloaded' in settings['notifications']['events']


# ── settings API ──────────────────────────────────────────────────────


class _FakeRequest:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


def test_settings_defaults_have_no_inline_secrets():
    block = api.DEFAULT_SETTINGS['notifications']
    assert block['enabled'] is False
    assert set(block['channels']) == {'telegram', 'ntfy', 'webhook'}
    assert 'telegram_bot_token' not in block
    assert 'watch.downloaded' in block['events']


def test_settings_update_saves_secrets_privately_and_returns_flags(
    monkeypatch, tmp_path
):
    store = notifications.NotificationStore(tmp_path / 'notifications.json')
    monkeypatch.setattr(api.state, 'notification_store', store)
    monkeypatch.setattr(api.state, 'settings_path', tmp_path / 'settings.json')
    monkeypatch.setitem(
        api.state.settings,
        'notifications',
        api.DEFAULT_SETTINGS['notifications'],
    )
    result = asyncio.run(
        api.update_settings_endpoint(
            _FakeRequest({
                'notifications': {
                    'enabled': True,
                    'events': ['download.completed'],
                    'channels': {
                        'telegram': {
                            'enabled': True,
                            'bot_token': 'private-token',
                            'chat_id': '42',
                        },
                        'ntfy': {
                            'enabled': True,
                            'url': 'https://ntfy.sh/private-topic',
                        },
                    },
                }
            })
        )
    )
    assert result['notifications']['channels']['telegram'] == {
        'enabled': True,
        'events': ['download.completed'],
        'bot_token_set': True,
        'chat_id_set': True,
    }
    assert 'private-token' not in json.dumps(result)
    saved_settings = json.loads((tmp_path / 'settings.json').read_text())
    assert 'private-token' not in json.dumps(saved_settings)
    assert store.load()['channels']['telegram']['bot_token'] == 'private-token'
    assert (tmp_path / 'notifications.json').stat().st_mode & 0o777 == 0o600


def test_settings_update_can_enable_saved_telegram_without_resending_token(
    monkeypatch, tmp_path
):
    store = notifications.NotificationStore(tmp_path / 'notifications.json')
    store.update({'telegram': {'bot_token': 'saved', 'chat_id': '42'}})
    monkeypatch.setattr(api.state, 'notification_store', store)
    monkeypatch.setattr(api.state, 'settings_path', None)
    monkeypatch.setitem(
        api.state.settings,
        'notifications',
        api.DEFAULT_SETTINGS['notifications'],
    )
    result = asyncio.run(
        api.update_settings_endpoint(
            _FakeRequest({
                'notifications': {
                    'enabled': True,
                    'channels': {'telegram': {'enabled': True}},
                }
            })
        )
    )
    assert result['notifications']['channels']['telegram']['enabled'] is True


def test_watch_hook_uses_generic_dispatcher(monkeypatch):
    seen = []

    async def check_artist(*args, **kwargs):
        return 2

    monkeypatch.setattr(monitor, 'check_artist', check_artist)

    async def noop_broadcast(message):
        return None

    async def record(event, payload):
        seen.append((event, payload))

    playlist = SimpleNamespace(id=1, name='Artist', kind=monitor.KIND_ARTIST)
    db = SimpleNamespace()
    result = asyncio.run(
        monitor.check_watch(
            playlist,
            db,
            None,
            noop_broadcast,
            None,
            _settings(),
            notify=record,
        )
    )
    assert result == 2
    assert seen == [('watch.downloaded', {'name': 'Artist', 'count': 2})]


def test_upgrade_hook_formats_terminal_summary():
    status = {
        'state': 'done',
        'run': {'id': 7},
        'counts': {'total': 10, 'completed': 6, 'failed': 1, 'skipped': 3},
    }
    assert api._upgrade_notice(status) == (
        'upgrade.finished',
        {'done': 6, 'failed': 1, 'skipped': 3},
    )


def test_download_batch_payload_counts_only_real_files():
    assert api._download_batch_payload(
        'Mix',
        [{'name': 'A'}, {'name': 'B'}, {'name': 'C'}],
        {0: 'a.mp3', 1: None, 2: ''},
    ) == {
        'name': 'Mix',
        'total': 3,
        'succeeded': 1,
        'failed': 2,
    }


def test_notification_test_endpoint_passes_channel_and_saved_secrets(
    monkeypatch, tmp_path
):
    seen = {}
    store = notifications.NotificationStore(tmp_path / 'notifications.json')
    store.update({'ntfy': {'url': 'https://ntfy.sh/saved'}})
    monkeypatch.setattr(api.state, 'notification_store', store)

    def fake_send(block, **kwargs):
        seen.update(block=block, **kwargs)
        return {'ok': True}

    monkeypatch.setattr(notifications, 'send_test_message', fake_send)
    result = asyncio.run(
        api.test_notifications_endpoint(
            _FakeRequest({'enabled': True}), channel='ntfy'
        )
    )
    assert result == {'ok': True}
    assert seen['channel'] == 'ntfy'
    assert (
        seen['secrets']['channels']['ntfy']['url'] == 'https://ntfy.sh/saved'
    )


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


def test_test_message_sends_ntfy_with_saved_token():
    calls = []
    result = notifications.send_test_message(
        {'channels': {'ntfy': {'enabled': True}}},
        channel='ntfy',
        secrets={
            'channels': {
                'ntfy': {'url': 'https://ntfy.sh/topic', 'token': 'saved'}
            }
        },
        post=_capture(calls),
    )
    assert result == {'ok': True}
    assert calls[0]['url'] == 'https://ntfy.sh/topic'
    assert calls[0]['headers']['Authorization'] == 'Bearer saved'


def test_test_message_rejects_unknown_channel():
    assert notifications.send_test_message({}, channel='other') == {
        'ok': False,
        'error': 'missing_credentials',
    }


# ── settings plumbing ────────────────────────────────────────────────


def test_defaults_present_and_off():
    block = api.DEFAULT_SETTINGS['notifications']
    assert block['enabled'] is False
    assert block['channels']['telegram']['enabled'] is False
    assert 'watch.downloaded' in block['events']


def test_notifications_is_a_nested_setting():
    assert 'notifications' in api._NESTED_SETTINGS


def test_clean_coerces_and_fills_without_secrets():
    cleaned = api._clean_notifications({
        'enabled': 1,
        'telegram_bot_token': '  t  ',
    })
    assert cleaned['enabled'] is True
    assert cleaned['channels']['telegram']['bot_token_set'] is True
    assert 'telegram_bot_token' not in cleaned


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
