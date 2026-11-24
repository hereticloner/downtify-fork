"""Read-only Telegram commands for the configured administrator chat."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Optional

import httpx
from loguru import logger

from . import notifications


class TelegramCommandBot:
    """Long-poll Telegram and answer /help, /status and /queue only."""

    def __init__(
        self,
        *,
        token: str,
        admin_chat_id: str,
        client: Optional[httpx.AsyncClient] = None,
        status_provider: Optional[Callable[[], dict[str, Any]]] = None,
        queue_provider: Optional[Callable[[], list[dict[str, Any]]]] = None,
        settings_provider: Optional[Callable[[], dict[str, Any]]] = None,
        secrets_provider: Optional[Callable[[], dict[str, Any]]] = None,
        poll_timeout: int = 30,
        retry_delay: float = 3.0,
    ) -> None:
        self.token = token
        self.admin_chat_id = str(admin_chat_id)
        self.client = client
        self.status_provider = status_provider or (lambda: {})
        self.queue_provider = queue_provider or (lambda: [])
        self.settings_provider = settings_provider
        self.secrets_provider = secrets_provider
        self.poll_timeout = poll_timeout
        self.retry_delay = retry_delay
        self.last_poll_failed = False
        self.active_token = ''
        self.configured = self.refresh_config()
        self.active_token = self.token if self.configured else ''

    def refresh_config(self) -> bool:
        """Re-read runtime settings so chat/token changes need no restart."""

        if self.settings_provider is None or self.secrets_provider is None:
            return bool(self.token and self.admin_chat_id)
        try:
            settings = self.settings_provider()
            secrets = self.secrets_provider()
            config = (
                notifications
                .effective_settings(settings, secrets)
                .get('notifications', {})
                .get('channels', {})
                .get('telegram', {})
            )
            block = (
                settings.get('notifications')
                if isinstance(settings, dict)
                else None
            )
            enabled = (
                isinstance(block, dict)
                and bool(block.get('enabled'))
                and isinstance(config, dict)
                and bool(config.get('enabled'))
            )
            token = str(config.get('bot_token') or '').strip()
            chat_id = str(config.get('chat_id') or '').strip()
            self.configured = bool(enabled and token and chat_id)
            self.token = token if self.configured else ''
            self.admin_chat_id = chat_id if self.configured else ''
            return self.configured
        except Exception:
            self.configured = False
            self.token = ''
            self.admin_chat_id = ''
            return False

    @classmethod
    def from_settings(
        cls,
        settings: Any,
        secrets: Any,
        **kwargs: Any,
    ) -> Optional['TelegramCommandBot']:
        block = (
            settings.get('notifications')
            if isinstance(settings, dict)
            else None
        )
        config = (
            notifications
            .effective_settings(settings, secrets)
            .get('notifications', {})
            .get('channels', {})
            .get('telegram', {})
        )
        if not isinstance(block, dict) or not block.get('enabled'):
            return None
        if not isinstance(config, dict) or not config.get('enabled'):
            return None
        token = str(config.get('bot_token') or '').strip()
        chat_id = str(config.get('chat_id') or '').strip()
        if not token or not chat_id:
            return None
        return cls(token=token, admin_chat_id=chat_id, **kwargs)

    async def handle_update(self, update: dict[str, Any]) -> None:
        if not self.refresh_config():
            return
        message = update.get('message') if isinstance(update, dict) else None
        if not isinstance(message, dict):
            return
        chat = (
            message.get('chat')
            if isinstance(message.get('chat'), dict)
            else {}
        )
        if str(chat.get('id') or '') != self.admin_chat_id:
            return
        text = str(message.get('text') or '').strip()
        command = (
            text.split(maxsplit=1)[0].split('@', 1)[0].lower() if text else ''
        )
        if command == '/help':
            await self._reply(
                'Downtify commands:\n'
                '/status — server and queue summary\n'
                '/queue — current download queue\n'
                '/help — this message\n\n'
                'Commands are read-only.'
            )
        elif command == '/status':
            status = self.status_provider()
            queue = status.get('queue') or {}
            await self._reply(
                f'Downtify {status.get("version") or "4.0.0"}\n'
                f'Queue: {queue.get("state") or "running"} · '
                f'{queue.get("active") or 0} active · '
                f'{queue.get("queued") or 0} waiting'
            )
        elif command == '/queue':
            jobs = self.queue_provider()
            if not jobs:
                await self._reply('Download queue is empty.')
                return
            lines = []
            for job in jobs[:20]:
                song = job.get('song') or {}
                title = str(song.get('name') or song.get('title') or 'Track')
                artist = str(
                    (song.get('artists') or [''])[0]
                    or song.get('artist')
                    or ''
                )
                lines.append(
                    f'{job.get("status") or "queued"} — {title}'
                    + (f' — {artist}' if artist else '')
                )
            suffix = f'\n… and {len(jobs) - 20} more' if len(jobs) > 20 else ''
            await self._reply('\n'.join(lines) + suffix)

    async def poll_once(self, offset: int) -> int:
        if self.client is None or not self.refresh_config():
            return offset
        if self.token != self.active_token:
            offset = 0
            self.active_token = self.token
        try:
            response = await self.client.get(
                f'{notifications.TELEGRAM_API}/bot{self.token}/getUpdates',
                params={
                    'offset': offset,
                    'timeout': self.poll_timeout,
                    'allowed_updates': json.dumps(['message']),
                },
            )
            response.raise_for_status()
            data = response.json()
            self.last_poll_failed = False
            for update in data.get('result') or []:
                await self.handle_update(update)
                try:
                    offset = max(offset, int(update['update_id']) + 1)
                except (KeyError, TypeError, ValueError):
                    pass
            return offset
        except Exception as exc:
            self.last_poll_failed = True
            logger.warning(
                'Telegram command poll failed ({})', type(exc).__name__
            )
            return offset

    async def run(self) -> None:
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(
            timeout=self.poll_timeout + 10
        )
        self.client = client
        offset = 0
        try:
            while True:
                offset = await self.poll_once(offset)
                if self.last_poll_failed or not self.configured:
                    await asyncio.sleep(self.retry_delay)
        finally:
            if owns_client:
                await client.aclose()

    async def _reply(self, text: str) -> None:
        if self.client is None:
            return
        try:
            await self.client.post(
                f'{notifications.TELEGRAM_API}/bot{self.token}/sendMessage',
                json={
                    'chat_id': self.admin_chat_id,
                    'text': text[:4000],
                    'disable_web_page_preview': True,
                },
            )
        except Exception as exc:
            logger.warning(
                'Telegram command reply failed ({})', type(exc).__name__
            )
