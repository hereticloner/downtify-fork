"""Outbound notifications for background events.

Today this is Telegram only: playlist and artist watches that download
new tracks announce it in a bot chat. Sending is best-effort - a missing
configuration or a network error is logged and swallowed, so a failed
notification can never fail the download sweep that triggered it. The
same module backs the Settings page's "send test message" button.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Callable, Optional

import httpx
from loguru import logger

TELEGRAM_API = 'https://api.telegram.org'
#: Short timeout: a notification must never hold up a download sweep.
TIMEOUT_SECONDS = 6.0

EVENT_TYPES = (
    'watch.downloaded',
    'download.completed',
    'download.failed',
    'download.batch',
    'upgrade.started',
    'upgrade.finished',
    'upgrade.failed',
    'backup.completed',
    'backup.failed',
)
_SECRET_FIELDS = {
    'telegram': ('bot_token', 'chat_id'),
    'ntfy': ('url', 'token'),
    'webhook': ('url', 'token'),
}


class NotificationStore:
    """Versioned notification secrets, atomically stored with mode 0600."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return {'version': 1}
        return data if isinstance(data, dict) else {'version': 1}

    def update(self, values: dict[str, Any]) -> None:
        data = self.load()
        channels = data.setdefault('channels', {})
        for name, fields in values.items():
            if not isinstance(fields, dict):
                continue
            current = channels.setdefault(name, {})
            for key, value in fields.items():
                text = str(value or '').strip()
                if text:
                    current[key] = text
        data['version'] = 1
        self.save(data)

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        partial = self.path.with_name(f'.{self.path.name}.partial')
        payload = json.dumps(data, indent=2).encode('utf-8')
        fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, 'wb') as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            if json.loads(partial.read_text(encoding='utf-8')) != data:
                raise ValueError('notification secrets failed read-back')
            os.replace(partial, self.path)
            self.path.chmod(0o600)
        finally:
            partial.unlink(missing_ok=True)


def clean_settings(
    value: Any, secrets: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """Public notification settings: switches and `<field>_set` flags only."""

    saved = secrets if isinstance(secrets, dict) else {}
    channels = (
        saved.get('channels')
        if isinstance(saved.get('channels'), dict)
        else {}
    )
    raw = value if isinstance(value, dict) else {}
    out: dict[str, Any] = {
        'enabled': bool(raw.get('enabled')),
        'events': [
            event
            for event in EVENT_TYPES
            if event in (raw.get('events') or [])
        ],
        'channels': {},
    }
    raw_channels = (
        raw.get('channels') if isinstance(raw.get('channels'), dict) else {}
    )
    for name, fields in _SECRET_FIELDS.items():
        config = (
            raw_channels.get(name)
            if isinstance(raw_channels.get(name), dict)
            else {}
        )
        stored = (
            channels.get(name) if isinstance(channels.get(name), dict) else {}
        )
        enabled = bool(config.get('enabled'))
        if name == 'telegram' and 'enabled' not in config:
            enabled = bool(raw.get('telegram_enabled'))
        public = {'enabled': enabled}
        events = config.get('events')
        if not isinstance(events, list):
            events = raw.get('events')
        public['events'] = [
            event for event in EVENT_TYPES if event in (events or [])
        ]
        for field in fields:
            supplied = str(config.get(field) or '').strip()
            if name == 'telegram' and not supplied:
                legacy = {
                    'bot_token': raw.get('telegram_bot_token'),
                    'chat_id': raw.get('telegram_chat_id'),
                }
                supplied = str(legacy.get(field) or '').strip()
            public[f'{field}_set'] = bool(
                supplied or str(stored.get(field) or '').strip()
            )
        out['channels'][name] = public
    if 'events' not in raw and raw.get('notify_watch_downloads', True):
        out['events'] = ['watch.downloaded']
    return out


def effective_settings(
    settings: Any, secrets: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """Copy settings with saved secrets injected for the dispatcher only."""

    out = copy.deepcopy(settings) if isinstance(settings, dict) else {}
    block = out.setdefault('notifications', clean_settings({}, secrets))
    channels = block.setdefault('channels', {})
    stored = (secrets or {}).get('channels') or {}
    for name, fields in _SECRET_FIELDS.items():
        config = channels.setdefault(name, {'enabled': False})
        source = stored.get(name) if isinstance(stored.get(name), dict) else {}
        for field in fields:
            if source.get(field):
                config[field] = source[field]
    return out


def migrate_legacy_settings(
    settings: dict[str, Any], store: 'NotificationStore'
) -> bool:
    """Move inline Telegram credentials into the private store once."""

    block = settings.get('notifications')
    if not isinstance(block, dict):
        return False
    values = {
        'telegram': {
            'bot_token': str(block.get('telegram_bot_token') or '').strip(),
            'chat_id': str(block.get('telegram_chat_id') or '').strip(),
        }
    }
    if not any(values['telegram'].values()):
        return False
    store.update(values)
    settings['notifications'] = clean_settings(block, store.load())
    return True


def telegram_credentials(block: Any) -> Optional[dict[str, str]]:
    """The bot token and chat id from a ``notifications`` block, or None.

    ``None`` means the credentials are incomplete, not that Telegram is
    off - the Settings test button sends with whatever is in the form.
    """
    if not isinstance(block, dict):
        return None
    token = str(block.get('telegram_bot_token') or '').strip()
    chat_id = str(block.get('telegram_chat_id') or '').strip()
    if not token or not chat_id:
        return None
    return {'bot_token': token, 'chat_id': chat_id}


def active_telegram_config(settings: Any) -> Optional[dict[str, str]]:
    """Credentials to use for event notifications, or None when off.

    Notifications have to be on as a whole *and* for Telegram, and the
    credentials have to be present; anything missing means "stay quiet".
    """
    if not isinstance(settings, dict):
        return None
    block = settings.get('notifications')
    if not isinstance(block, dict):
        return None
    if not block.get('enabled') or not block.get('telegram_enabled'):
        return None
    return telegram_credentials(block)


def format_watch_downloads(name: str, count: int) -> str:
    """The message for a watch that pulled in ``count`` new tracks."""
    track = 'track' if count == 1 else 'tracks'
    return f'Downtify downloaded {count} new {track} from "{name}"'


def format_event(event: str, payload: dict[str, Any]) -> str:
    """One human-readable line for an event, without credentials or URLs."""

    if event == 'watch.downloaded':
        return format_watch_downloads(
            str(payload.get('name') or 'watch'), int(payload.get('count') or 0)
        )
    if event == 'download.completed':
        title = str(payload.get('title') or 'Track')
        artist = str(payload.get('artist') or '').strip()
        return f'Downtify downloaded {title}' + (
            f' by {artist}' if artist else ''
        )
    if event == 'download.failed':
        title = str(payload.get('title') or 'Track')
        reason = str(payload.get('message') or payload.get('code') or 'failed')
        return f'Downtify could not download {title}: {reason[:200]}'
    if event == 'download.batch':
        name = str(payload.get('name') or 'batch')
        return (
            f'Downtify finished "{name}": '
            f'{int(payload.get("succeeded") or 0)} downloaded, '
            f'{int(payload.get("failed") or 0)} failed'
        )
    if event == 'upgrade.started':
        return f'Library upgrade started ({int(payload.get("count") or 0)} tracks)'
    if event == 'upgrade.finished':
        return (
            'Library upgrade finished: '
            f'{int(payload.get("done") or 0)} updated, '
            f'{int(payload.get("failed") or 0)} failed, '
            f'{int(payload.get("skipped") or 0)} skipped'
        )
    if event == 'upgrade.failed':
        return 'Library upgrade failed'
    if event == 'backup.completed':
        return f'Backup completed: {payload.get("name") or "backup"}'
    if event == 'backup.failed':
        return 'Backup failed'
    return f'Downtify: {event}'


def _channel_config(block: dict[str, Any], name: str) -> dict[str, Any]:
    channels = block.get('channels')
    if isinstance(channels, dict) and isinstance(channels.get(name), dict):
        return channels[name]
    if name == 'telegram':
        return {
            'enabled': bool(block.get('telegram_enabled')),
            'bot_token': block.get('telegram_bot_token') or '',
            'chat_id': block.get('telegram_chat_id') or '',
        }
    return {}


def _event_enabled(
    block: dict[str, Any], channel: dict[str, Any], event: str
) -> bool:
    events = channel.get('events')
    if isinstance(events, list):
        return event in events
    events = block.get('events')
    if isinstance(events, list):
        return event in events
    if event == 'watch.downloaded':
        return bool(block.get('notify_watch_downloads', True))
    return False


def _post_json(
    sender: Callable[..., Any],
    url: str,
    payload: dict[str, Any],
    *,
    headers: Optional[dict[str, str]] = None,
) -> bool:
    try:
        response = sender(
            url, json=payload, timeout=TIMEOUT_SECONDS, headers=headers or {}
        )
        status = int(response.status_code)
        if not 200 <= status < 300:
            logger.warning('Notification channel rejected (HTTP {})', status)
        return 200 <= status < 300
    except Exception as exc:
        # Exception text can contain a token-bearing URL; never log it.
        logger.warning('Notification channel failed ({})', type(exc).__name__)
        return False


class Telegram:
    name = 'telegram'

    @staticmethod
    def send(
        config: dict[str, Any],
        message: str,
        event: str,
        payload: dict[str, Any],
        post: Callable[..., Any],
    ) -> bool:
        token = str(config.get('bot_token') or '').strip()
        chat_id = str(config.get('chat_id') or '').strip()
        if not token or not chat_id:
            return False
        return _post_json(
            post,
            f'{TELEGRAM_API}/bot{token}/sendMessage',
            {
                'chat_id': chat_id,
                'text': message,
                'disable_web_page_preview': True,
            },
        )


class Ntfy:
    name = 'ntfy'

    @staticmethod
    def send(
        config: dict[str, Any],
        message: str,
        event: str,
        payload: dict[str, Any],
        post: Callable[..., Any],
    ) -> bool:
        url = str(config.get('url') or '').strip()
        if not url.startswith(('https://', 'http://')):
            return False
        headers = {'Title': 'Downtify', 'Tags': 'music'}
        token = str(config.get('token') or '').strip()
        if token:
            headers['Authorization'] = f'Bearer {token}'
        return _post_json(post, url, message, headers=headers)


class Webhook:
    name = 'webhook'

    @staticmethod
    def send(
        config: dict[str, Any],
        message: str,
        event: str,
        payload: dict[str, Any],
        post: Callable[..., Any],
    ) -> bool:
        url = str(config.get('url') or '').strip()
        if not url.startswith(('https://', 'http://')):
            return False
        headers = {'Content-Type': 'application/json'}
        token = str(config.get('token') or '').strip()
        if token:
            headers['Authorization'] = f'Bearer {token}'
        return _post_json(
            post,
            url,
            {'event': event, 'message': message, 'payload': payload},
            headers=headers,
        )


class Dispatcher:
    """Fan out one event to the enabled, subscribed channels."""

    def __init__(self, *, post: Optional[Callable[..., Any]] = None) -> None:
        self.post = post or httpx.post
        self.channels = (Telegram(), Ntfy(), Webhook())

    def dispatch(
        self, settings: Any, event: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        block = (
            settings.get('notifications')
            if isinstance(settings, dict)
            else None
        )
        if not isinstance(block, dict) or not block.get('enabled'):
            return {'ok': True, 'sent': [], 'failed': []}
        message = format_event(event, payload)
        sent: list[str] = []
        failed: list[str] = []
        for channel in self.channels:
            config = _channel_config(block, channel.name)
            if not config.get('enabled') or not _event_enabled(
                block, config, event
            ):
                continue
            if channel.send(config, message, event, payload, self.post):
                sent.append(channel.name)
            else:
                failed.append(channel.name)
        return {'ok': not failed, 'sent': sent, 'failed': failed}


def notify_event(
    settings: Any,
    event: str,
    payload: dict[str, Any],
    *,
    post: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Best-effort event delivery; callers never fail because of it."""

    return Dispatcher(post=post).dispatch(settings, event, payload)


def send_telegram(
    message: str,
    config: dict[str, str],
    *,
    post: Optional[Callable[..., Any]] = None,
) -> bool:
    """POST ``message`` to the bot chat; True on a 2xx answer.

    Any failure (network, non-2xx, bad config) returns False and is
    logged - callers treat a notification as fire-and-forget. ``post``
    is the injection point tests use to avoid the network.
    """
    url = f'{TELEGRAM_API}/bot{config["bot_token"]}/sendMessage'
    payload = {
        'chat_id': config['chat_id'],
        'text': message,
        'disable_web_page_preview': True,
    }
    sender = post or httpx.post
    try:
        response = sender(url, json=payload, timeout=TIMEOUT_SECONDS)
        status = int(response.status_code)
        if not 200 <= status < 300:
            logger.warning('Telegram notification rejected (HTTP {})', status)
        return 200 <= status < 300
    except Exception as exc:
        # Exception text can contain the token-bearing Telegram URL.
        logger.warning('Telegram notification failed ({})', type(exc).__name__)
        return False


def notify_watch_downloads(
    settings: Any,
    name: str,
    count: int,
    *,
    post: Optional[Callable[..., Any]] = None,
) -> bool:
    """Send the "N new tracks from <watch>" notice, if it is enabled."""
    if count <= 0:
        return False
    block = (
        settings.get('notifications') if isinstance(settings, dict) else None
    )
    if isinstance(block, dict) and not block.get(
        'notify_watch_downloads', True
    ):
        return False
    config = active_telegram_config(settings)
    if config is None:
        return False
    return send_telegram(
        format_watch_downloads(name, count), config, post=post
    )


def send_test_message(
    block: Any,
    *,
    channel: str = 'telegram',
    secrets: Optional[dict[str, Any]] = None,
    post: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Send a canned test message for one channel without saving it.

    Accepts both the legacy flat Telegram block and the new channel map.
    Typed credentials override saved ones; an empty field keeps the saved
    secret. Returns ``{ok, error?}`` and never includes credentials.
    """

    raw = block if isinstance(block, dict) else {}
    if channel == 'telegram' and telegram_credentials(raw) is not None:
        ok = send_telegram(
            'Downtify test notification \u2713',
            telegram_credentials(raw) or {},
            post=post,
        )
        return {'ok': ok, **({} if ok else {'error': 'send_failed'})}

    effective = effective_settings({'notifications': raw}, secrets)
    config = (effective['notifications'].get('channels') or {}).get(channel)
    if not isinstance(config, dict):
        return {'ok': False, 'error': 'missing_credentials'}
    supplied = (raw.get('channels') or {}).get(channel) or {}
    for field in _SECRET_FIELDS.get(channel, ()):
        if supplied.get(field):
            config[field] = supplied[field]
    sender = {item.name: item for item in (Telegram(), Ntfy(), Webhook())}.get(
        channel
    )
    required = {
        'telegram': ('bot_token', 'chat_id'),
        'ntfy': ('url',),
        'webhook': ('url',),
    }.get(channel)
    if (
        sender is None
        or not required
        or any(not str(config.get(field) or '').strip() for field in required)
    ):
        return {'ok': False, 'error': 'missing_credentials'}
    ok = sender.send(
        config,
        'Downtify test notification \u2713',
        'test',
        {},
        post or httpx.post,
    )
    return {'ok': ok, **({} if ok else {'error': 'send_failed'})}
