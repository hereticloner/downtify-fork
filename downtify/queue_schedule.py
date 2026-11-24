"""Time-window control for starting new downloads."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from loguru import logger

DEFAULT_QUEUE_CONTROL = {
    'quiet_hours': {
        'enabled': False,
        'start': '22:00',
        'end': '08:00',
        'timezone': 'Europe/Istanbul',
    }
}
_TIME_RE = re.compile(r'^([01]\d|2[0-3]):([0-5]\d)$')


def _clock(value: Any, default: str) -> int:
    text = str(value or default).strip()
    match = _TIME_RE.fullmatch(text)
    if match is None:
        raise ValueError('quiet hours must use HH:MM')
    return int(match[1]) * 60 + int(match[2])


def _enabled(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'on'}
    return bool(value)


def clean_queue_control(value: Any) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    quiet = raw.get('quiet_hours')
    quiet = quiet if isinstance(quiet, dict) else {}
    start = str(
        quiet.get('start') or DEFAULT_QUEUE_CONTROL['quiet_hours']['start']
    )
    end = str(quiet.get('end') or DEFAULT_QUEUE_CONTROL['quiet_hours']['end'])
    tz = str(
        quiet.get('timezone')
        or DEFAULT_QUEUE_CONTROL['quiet_hours']['timezone']
    ).strip()
    _clock(start, start)
    _clock(end, end)
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError('unknown quiet-hours timezone') from exc
    return {
        'quiet_hours': {
            'enabled': _enabled(quiet.get('enabled')),
            'start': start,
            'end': end,
            'timezone': tz,
        }
    }


def quiet_hours(settings: Any, now: datetime | None = None) -> bool:
    config = clean_queue_control(
        settings.get('queue_control') if isinstance(settings, dict) else None
    )['quiet_hours']
    if not config['enabled']:
        return False
    start = _clock(config['start'], config['start'])
    end = _clock(config['end'], config['end'])
    if start == end:
        return False
    zone = ZoneInfo(config['timezone'])
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=zone)
    local = current.astimezone(zone)
    minute = local.hour * 60 + local.minute
    if start < end:
        return start <= minute < end
    return minute >= start or minute < end


class QueueSchedule:
    """Apply quiet-hours changes to a pause gate only on transitions."""

    def __init__(
        self,
        settings_provider: Callable[[], dict[str, Any]],
        set_quiet: Callable[[bool], None],
    ) -> None:
        self.settings_provider = settings_provider
        self.set_quiet = set_quiet
        self.active: bool | None = None

    def apply(self, now: datetime | None = None) -> bool:
        active = quiet_hours(self.settings_provider(), now)
        if active != self.active:
            self.set_quiet(active)
            self.active = active
        return active


async def schedule_loop(
    settings_provider: Callable[[], dict[str, Any]],
    set_quiet: Callable[[bool], None],
    interval: float = 30,
    on_change: Optional[Callable[[bool], Awaitable[None]]] = None,
) -> None:
    schedule = QueueSchedule(settings_provider, set_quiet)
    while True:
        try:
            previous = schedule.active
            active = schedule.apply()
            if on_change is not None and active != previous:
                await on_change(active)
        except Exception:
            logger.exception('Queue quiet-hours update failed')
        await asyncio.sleep(interval)
