from __future__ import annotations

import httpx
import pytest

from downtify import notifications
from downtify.telegram_commands import TelegramCommandBot


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    async def get(self, url, **kwargs):
        self.requests.append((url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return httpx.Response(
            200,
            json=response,
            request=httpx.Request('GET', url),
        )

    async def post(self, url, **kwargs):
        self.requests.append((url, kwargs))
        return httpx.Response(
            200,
            json={'ok': True},
            request=httpx.Request('POST', url),
        )


def _bot(client, **overrides):
    options = {
        'token': '123:secret',
        'admin_chat_id': '42',
        'client': client,
        'status_provider': lambda: {
            'version': '4.0.0',
            'queue': {'active': 0},
        },
        'queue_provider': lambda: [],
    }
    options.update(overrides)
    return TelegramCommandBot(**options)


@pytest.mark.asyncio
async def test_unauthorized_chat_is_ignored_without_a_reply():
    client = FakeClient([{'ok': True, 'result': []}])
    bot = _bot(client)

    await bot.handle_update({
        'update_id': 1,
        'message': {'chat': {'id': 99}, 'text': '/status'},
    })

    assert client.requests == []


@pytest.mark.asyncio
async def test_help_replies_only_to_the_admin_chat():
    client = FakeClient([{'ok': True, 'result': []}])
    bot = _bot(client)

    await bot.handle_update({
        'update_id': 1,
        'message': {'chat': {'id': 42}, 'text': '/help'},
    })

    assert len(client.requests) == 1
    url, kwargs = client.requests[0]
    assert url == 'https://api.telegram.org/bot123:secret/sendMessage'
    assert kwargs['json']['chat_id'] == '42'
    assert '/status' in kwargs['json']['text']
    assert '/queue' in kwargs['json']['text']


@pytest.mark.asyncio
async def test_status_and_queue_are_read_only_views():
    client = FakeClient([{'ok': True, 'result': []}])
    bot = _bot(
        client,
        status_provider=lambda: {
            'version': '4.0.0',
            'queue': {'active': 1, 'queued': 2},
        },
        queue_provider=lambda: [
            {
                'status': 'downloading',
                'song': {'name': 'One', 'artists': ['A']},
            }
        ],
    )

    await bot.handle_update({
        'update_id': 1,
        'message': {'chat': {'id': 42}, 'text': '/status'},
    })
    await bot.handle_update({
        'update_id': 2,
        'message': {'chat': {'id': 42}, 'text': '/queue'},
    })

    assert len(client.requests) == 2
    assert '4.0.0' in client.requests[0][1]['json']['text']
    assert 'downloading' in client.requests[1][1]['json']['text']
    assert 'One' in client.requests[1][1]['json']['text']
    assert all(url.endswith('/sendMessage') for url, _ in client.requests)


@pytest.mark.asyncio
async def test_unknown_or_write_command_gets_no_action():
    client = FakeClient([{'ok': True, 'result': []}])
    bot = _bot(client)
    for command in ('/pause', '/resume', '/delete', '/unknown'):
        await bot.handle_update({
            'update_id': 1,
            'message': {'chat': {'id': 42}, 'text': command},
        })
    assert client.requests == []


@pytest.mark.asyncio
async def test_poll_once_advances_offset_past_unauthorized_updates():
    client = FakeClient([
        {
            'ok': True,
            'result': [
                {
                    'update_id': 7,
                    'message': {'chat': {'id': 99}, 'text': '/status'},
                },
                {
                    'update_id': 8,
                    'message': {'chat': {'id': 42}, 'text': '/help'},
                },
            ],
        }
    ])
    bot = _bot(client)

    offset = await bot.poll_once(0)

    assert offset == 9
    assert client.requests[0][1]['params']['offset'] == 0
    assert len(client.requests) == 2


@pytest.mark.asyncio
async def test_poll_once_survives_network_failure_without_logging_token():
    client = FakeClient([OSError('failed for bot123:secret')])
    warnings = []
    original = notifications.logger.warning
    notifications.logger.warning = lambda message, *args: warnings.append((
        message,
        args,
    ))
    try:
        bot = _bot(client)
        assert await bot.poll_once(0) == 0
    finally:
        notifications.logger.warning = original
    assert '123:secret' not in repr(warnings)


def test_from_settings_requires_enabled_telegram_credentials():
    client = FakeClient([])
    assert (
        TelegramCommandBot.from_settings(
            {'notifications': {'enabled': False}},
            {'channels': {'telegram': {'bot_token': 't', 'chat_id': '42'}}},
            client=client,
        )
        is None
    )
    assert (
        TelegramCommandBot.from_settings(
            {
                'notifications': {
                    'enabled': True,
                    'channels': {'telegram': {'enabled': False}},
                }
            },
            {'channels': {'telegram': {'bot_token': 't', 'chat_id': '42'}}},
            client=client,
        )
        is None
    )
    bot = TelegramCommandBot.from_settings(
        {
            'notifications': {
                'enabled': True,
                'channels': {'telegram': {'enabled': True}},
            }
        },
        {'channels': {'telegram': {'bot_token': 't', 'chat_id': '42'}}},
        client=client,
    )
    assert bot is not None
    assert bot.admin_chat_id == '42'
