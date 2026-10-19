"""Quiet-pass interval relaxation and when a watch is next due (NG idea).

A playlist watch that produced no new downloads and no new tracks on
three passes in a row is checked 7x less often afterwards; one new track
resets the count. The list also says how far away the next check is, so
a watch that was checked days ago doesn't look like a stopped one.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from downtify import api
from downtify.monitor import (
    QUIET_PASS_RELAX_MULTIPLIER,
    QUIET_PASS_RELAX_THRESHOLD,
    PlaylistMonitorDB,
    effective_interval_minutes,
)

PLAYLIST = '37i9dQZF1DXcBWIGoYBM5M'
URL = f'https://open.spotify.com/playlist/{PLAYLIST}'


def _iso(moment: datetime) -> str:
    return moment.isoformat()


@pytest.fixture
def db(monkeypatch, tmp_path):
    store = PlaylistMonitorDB(tmp_path / 'monitor.db')
    monkeypatch.setattr(api.state, 'monitor_db', store)
    monkeypatch.setattr(api.state, 'downloader', None)
    return store


def _watch(db, **kwargs):
    return db.add_playlist(
        PLAYLIST,
        'Top Hits',
        URL,
        kwargs.pop('interval_minutes', 60),
        **kwargs,
    )


# ── effective_interval_minutes ──────────────────────────────────────────────


def test_effective_interval_no_relaxation_by_default():
    assert effective_interval_minutes(60, 0) == 60


def test_effective_interval_holds_below_the_threshold():
    # One or two empty passes are not a finished watch yet: the next
    # check still runs at the interval the user asked for.
    assert QUIET_PASS_RELAX_THRESHOLD == 3
    assert effective_interval_minutes(60, 1) == 60
    assert effective_interval_minutes(60, 2) == 60
    assert effective_interval_minutes(1440, 1) == 1440
    assert effective_interval_minutes(1440, 2) == 1440


def test_effective_interval_relaxes_at_the_threshold():
    assert (
        effective_interval_minutes(60, 3) == 60 * QUIET_PASS_RELAX_MULTIPLIER
    )
    assert effective_interval_minutes(1440, 3) == 1440 * 7
    assert effective_interval_minutes(60, 9) == 60 * 7


def test_effective_interval_resets_on_activity():
    assert effective_interval_minutes(60, 0) == 60


# ── next_due_minutes ────────────────────────────────────────────────────────


def test_next_due_minutes_counts_down_to_the_next_check(db):
    watch = _watch(db, interval_minutes=60)
    db.update_playlist(
        watch.id,
        last_checked=_iso(datetime.now(timezone.utc) - timedelta(minutes=5)),
    )
    (listed,) = asyncio.run(api.list_monitor_playlists())
    assert 55 <= listed['next_due_minutes'] <= 60


def test_next_due_minutes_zero_when_never_checked(db):
    _watch(db)
    (listed,) = asyncio.run(api.list_monitor_playlists())
    assert listed['next_due_minutes'] == 0


def test_next_due_minutes_zero_when_the_check_is_overdue(db):
    watch = _watch(db, interval_minutes=60)
    db.update_playlist(
        watch.id,
        last_checked=_iso(datetime.now(timezone.utc) - timedelta(days=30)),
    )
    (listed,) = asyncio.run(api.list_monitor_playlists())
    assert listed['next_due_minutes'] == 0


def test_next_due_minutes_follows_the_relaxed_interval(db):
    """A watch that is far enough past the threshold is counted from its
    own next due time (7x), not from the plain interval."""
    watch = _watch(db, interval_minutes=60)
    checked = datetime.now(timezone.utc) - timedelta(hours=6)
    db.update_playlist(watch.id, last_checked=_iso(checked), quiet_passes=3)
    (listed,) = asyncio.run(api.list_monitor_playlists())
    # Due 7 hours after the last check, six of which have passed.
    assert listed['next_due_minutes'] == 60


def test_next_due_minutes_ignores_a_plain_quiet_pass(db):
    """Below the threshold the interval isn't relaxed, so the next due
    time is the plain one - one empty pass must not push it out."""
    watch = _watch(db, interval_minutes=60)
    db.update_playlist(
        watch.id,
        last_checked=_iso(datetime.now(timezone.utc) - timedelta(hours=1)),
        quiet_passes=1,
    )
    (listed,) = asyncio.run(api.list_monitor_playlists())
    assert listed['next_due_minutes'] == 0


def test_next_due_minutes_zero_for_an_unparsable_timestamp(db):
    watch = _watch(db)
    db.update_playlist(watch.id, last_checked='not-a-date')
    (listed,) = asyncio.run(api.list_monitor_playlists())
    assert listed['next_due_minutes'] == 0


def test_list_does_not_change_the_watch_row(db):
    """The countdown is the route's, not the DB layer's."""
    watch = _watch(db)
    db.update_playlist(watch.id, last_checked=_iso(datetime.now(timezone.utc)))
    (listed,) = asyncio.run(api.list_monitor_playlists())
    assert 'next_due_minutes' not in db.get_playlist(watch.id).to_dict()
    assert 'next_due_minutes' in listed
