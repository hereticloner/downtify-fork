"""Quiet-pass interval relaxation (NG-fork idea, TDD).

A playlist watch that produced no new downloads and no new tracks on a
pass is checked 7x less often afterwards. One new track resets it.
"""

from __future__ import annotations

from downtify.monitor import effective_interval_minutes


def test_effective_interval_no_relaxation_by_default():
    assert effective_interval_minutes(60, 0) == 60


def test_effective_interval_relaxes_after_quiet_pass():
    # One fully quiet pass -> 7x the configured interval.
    assert effective_interval_minutes(60, 1) == 60 * 7
    assert effective_interval_minutes(1440, 2) == 1440 * 7


def test_effective_interval_resets_on_activity():
    assert effective_interval_minutes(60, 0) == 60
