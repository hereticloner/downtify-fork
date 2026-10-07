"""Outbound notifications for background events.

Today this is Telegram only: playlist and artist watches that download
new tracks announce it in a bot chat. Sending is best-effort - a missing
configuration or a network error is logged and swallowed, so a failed
notification can never fail the download sweep that triggered it. The
same module backs the Settings page's "send test message" button.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import httpx
from loguru import logger

TELEGRAM_API = 'https://api.telegram.org'
#: Short timeout: a notification must never hold up a download sweep.
TIMEOUT_SECONDS = 6.0


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
        logger.warning('Telegram notification failed: {}', exc)
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
    block: Any, *, post: Optional[Callable[..., Any]] = None
) -> dict[str, Any]:
    """Send a canned test message from a form's notification block.

    Works whether or not notifications are enabled: the point is to try
    the credentials as typed. Returns ``{ok, error?}``.
    """
    config = telegram_credentials(block)
    if config is None:
        return {'ok': False, 'error': 'missing_credentials'}
    ok = send_telegram('Downtify test notification \u2713', config, post=post)
    return {'ok': ok, **({} if ok else {'error': 'send_failed'})}
