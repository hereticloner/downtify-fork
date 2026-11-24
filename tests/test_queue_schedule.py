from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException

from downtify import api, notifications
from downtify.download_queue import QueuePause
from downtify.queue_schedule import (
    QueueSchedule,
    clean_queue_control,
    quiet_hours,
    schedule_loop,
)


def _settings(
    start='22:00', end='08:00', enabled=True, timezone='Europe/Istanbul'
):
    return {
        'queue_control': {
            'quiet_hours': {
                'enabled': enabled,
                'start': start,
                'end': end,
                'timezone': timezone,
            }
        }
    }


def _at(hour, minute=0, timezone='Europe/Istanbul'):
    return datetime(2026, 1, 15, hour, minute, tzinfo=ZoneInfo(timezone))


def test_quiet_hours_are_disabled_by_default():
    assert quiet_hours({}, _at(23)) is False
    assert quiet_hours(_settings(enabled=False), _at(23)) is False


def test_daytime_window_includes_start_and_excludes_end():
    settings = _settings(start='09:00', end='17:00')
    assert quiet_hours(settings, _at(8, 59)) is False
    assert quiet_hours(settings, _at(9)) is True
    assert quiet_hours(settings, _at(16, 59)) is True
    assert quiet_hours(settings, _at(17)) is False


def test_overnight_window_wraps_midnight():
    settings = _settings(start='22:00', end='08:00')
    assert quiet_hours(settings, _at(21, 59)) is False
    assert quiet_hours(settings, _at(22)) is True
    assert quiet_hours(settings, _at(23)) is True
    assert quiet_hours(settings, _at(0)) is True
    assert quiet_hours(settings, _at(7, 59)) is True
    assert quiet_hours(settings, _at(8)) is False


def test_equal_start_and_end_is_not_a_full_day_pause():
    assert quiet_hours(_settings(start='22:00', end='22:00'), _at(22)) is False


def test_dst_uses_local_wall_clock_on_both_transitions():
    spring = ZoneInfo('Europe/Istanbul')
    settings = _settings(start='00:00', end='04:00')
    assert (
        quiet_hours(settings, datetime(2026, 3, 29, 0, 30, tzinfo=spring))
        is True
    )
    assert (
        quiet_hours(settings, datetime(2026, 3, 29, 3, 30, tzinfo=spring))
        is True
    )
    assert (
        quiet_hours(settings, datetime(2026, 3, 29, 4, 0, tzinfo=spring))
        is False
    )

    fall = ZoneInfo('Europe/Istanbul')
    settings = _settings(start='01:00', end='02:00')
    first = datetime(2026, 10, 25, 1, 30, tzinfo=fall, fold=0)
    second = datetime(2026, 10, 25, 1, 30, tzinfo=fall, fold=1)
    assert quiet_hours(settings, first) is True
    assert quiet_hours(settings, second) is True
    assert (
        quiet_hours(settings, datetime(2026, 10, 25, 2, 0, tzinfo=fall))
        is False
    )


def test_clean_queue_control_fills_defaults_and_rejects_bad_values():
    cleaned = clean_queue_control({})
    assert cleaned == {
        'quiet_hours': {
            'enabled': False,
            'start': '22:00',
            'end': '08:00',
            'timezone': 'Europe/Istanbul',
        }
    }
    with pytest.raises(ValueError, match='HH:MM'):
        clean_queue_control({'quiet_hours': {'start': '25:00'}})
    with pytest.raises(ValueError, match='timezone'):
        clean_queue_control({'quiet_hours': {'timezone': 'Not/AZone'}})


def test_load_settings_merges_queue_control_defaults(tmp_path, monkeypatch):
    path = tmp_path / 'settings.json'
    path.write_text(
        '{"queue_control": {"quiet_hours": {"enabled": true}}}',
        encoding='utf-8',
    )
    monkeypatch.setattr(
        api.state,
        'notification_store',
        notifications.NotificationStore(tmp_path / 'notifications.json'),
    )

    settings = api._load_settings(path)

    assert settings['queue_control']['quiet_hours'] == {
        'enabled': True,
        'start': '22:00',
        'end': '08:00',
        'timezone': 'Europe/Istanbul',
    }


class _SettingsRequest:
    def __init__(self, payload):
        self.payload = payload

    async def json(self):
        return self.payload


@pytest.mark.asyncio
async def test_settings_update_validates_and_cleans_queue_control(monkeypatch):
    monkeypatch.setattr(api.state, 'settings', dict(api.DEFAULT_SETTINGS))
    monkeypatch.setattr(api.state, 'settings_path', None)
    monkeypatch.setattr(api.state, 'downloader', None)
    monkeypatch.setattr(api, 'log_activity', AsyncMock())

    with pytest.raises(HTTPException) as caught:
        await api.update_settings_endpoint(
            _SettingsRequest({
                'queue_control': {'quiet_hours': {'start': '25:00'}}
            })
        )
    assert caught.value.status_code == 400

    await api.update_settings_endpoint(
        _SettingsRequest({
            'queue_control': {
                'quiet_hours': {
                    'enabled': True,
                    'start': '23:00',
                    'end': '07:30',
                    'timezone': 'Europe/Istanbul',
                }
            }
        })
    )
    assert api.state.settings['queue_control']['quiet_hours'] == {
        'enabled': True,
        'start': '23:00',
        'end': '07:30',
        'timezone': 'Europe/Istanbul',
    }


def test_queue_schedule_applies_only_transitions():
    settings = _settings()
    changes = []
    schedule = QueueSchedule(lambda: settings, changes.append)

    assert schedule.apply(_at(23)) is True
    assert schedule.apply(_at(23, 30)) is True
    settings['queue_control']['quiet_hours']['enabled'] = False
    assert schedule.apply(_at(23, 45)) is False
    assert changes == [True, False]


@pytest.mark.asyncio
async def test_schedule_loop_applies_then_waits(monkeypatch):
    changes = []
    waits = []

    async def stop_after_wait(seconds):
        waits.append(seconds)
        raise asyncio.CancelledError

    monkeypatch.setattr(asyncio, 'sleep', stop_after_wait)
    with pytest.raises(asyncio.CancelledError):
        await schedule_loop(_settings, changes.append)

    assert changes == [True]
    assert waits == [30]


@pytest.mark.asyncio
async def test_schedule_loop_announces_transitions(monkeypatch):
    settings = _settings()
    changes = []
    announcements = []
    waits = 0

    async def announce(active):
        announcements.append(active)

    async def advance(seconds):
        nonlocal waits
        waits += 1
        if waits == 1:
            settings['queue_control']['quiet_hours']['enabled'] = False
            return
        raise asyncio.CancelledError

    monkeypatch.setattr(asyncio, 'sleep', advance)
    with pytest.raises(asyncio.CancelledError):
        await schedule_loop(
            lambda: settings, changes.append, on_change=announce
        )

    assert changes == [True, False]
    assert announcements == [True, False]


def test_manual_pause_wins_over_quiet_hours_and_survives_them_ending():
    pause = QueuePause()
    pause.set_quiet(True)
    pause.resume()
    assert pause.paused is True

    pause.set_quiet(False)
    assert pause.paused is False

    pause.pause()
    pause.set_quiet(True)
    pause.set_quiet(False)
    assert pause.paused is True
    pause.resume()
    assert pause.paused is False
