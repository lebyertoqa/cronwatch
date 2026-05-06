"""Tests for cronwatch.throttle."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from cronwatch.throttle import AlertThrottle, ThrottlePolicy


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _policy(**kwargs) -> ThrottlePolicy:
    defaults = dict(
        base_interval_seconds=60,
        backoff_multiplier=2.0,
        max_interval_seconds=3600,
        reset_on_success=True,
    )
    defaults.update(kwargs)
    return ThrottlePolicy(**defaults)


# ---------------------------------------------------------------------------
# ThrottlePolicy.interval_for
# ---------------------------------------------------------------------------

def test_interval_first_alert_equals_base():
    p = _policy(base_interval_seconds=60)
    assert p.interval_for(0) == 60.0


def test_interval_grows_with_consecutive_alerts():
    p = _policy(base_interval_seconds=60, backoff_multiplier=2.0)
    assert p.interval_for(1) == 60.0
    assert p.interval_for(2) == 120.0
    assert p.interval_for(3) == 240.0


def test_interval_capped_at_max():
    p = _policy(base_interval_seconds=60, backoff_multiplier=10.0, max_interval_seconds=200)
    assert p.interval_for(5) == 200.0


# ---------------------------------------------------------------------------
# AlertThrottle.allow — failure path
# ---------------------------------------------------------------------------

def test_first_failure_always_allowed():
    t = AlertThrottle(_policy())
    assert t.allow("job_a", success=False) is True


def test_second_failure_immediately_suppressed():
    t = AlertThrottle(_policy(base_interval_seconds=60))
    t.allow("job_a", success=False)          # first — allowed
    assert t.allow("job_a", success=False) is False


def test_failure_allowed_after_interval(monkeypatch):
    mono = [0.0]
    monkeypatch.setattr(time, "monotonic", lambda: mono[0])

    t = AlertThrottle(_policy(base_interval_seconds=60))
    t.allow("job_a", success=False)          # first alert at t=0

    mono[0] = 61.0                           # advance past base interval
    assert t.allow("job_a", success=False) is True


def test_backoff_increases_required_gap(monkeypatch):
    mono = [0.0]
    monkeypatch.setattr(time, "monotonic", lambda: mono[0])

    t = AlertThrottle(_policy(base_interval_seconds=60, backoff_multiplier=2.0))
    t.allow("job_a", success=False)          # alert 1 at t=0  (interval now 60)
    mono[0] = 61.0
    t.allow("job_a", success=False)          # alert 2 at t=61 (interval now 120)
    mono[0] = 120.0                          # only 59 s elapsed — suppressed
    assert t.allow("job_a", success=False) is False
    mono[0] = 182.0                          # 121 s elapsed — allowed
    assert t.allow("job_a", success=False) is True


# ---------------------------------------------------------------------------
# AlertThrottle.allow — success path
# ---------------------------------------------------------------------------

def test_success_never_triggers_alert():
    t = AlertThrottle(_policy())
    assert t.allow("job_a", success=True) is False


def test_success_resets_state_so_next_failure_is_immediate():
    t = AlertThrottle(_policy(base_interval_seconds=60))
    t.allow("job_a", success=False)          # alert 1
    t.allow("job_a", success=True)           # reset
    assert t.allow("job_a", success=False) is True  # fresh start


def test_success_no_reset_when_disabled():
    t = AlertThrottle(_policy(base_interval_seconds=60, reset_on_success=False))
    t.allow("job_a", success=False)          # alert 1 at t=0
    t.allow("job_a", success=True)           # no reset
    # immediately after, still within interval
    assert t.allow("job_a", success=False) is False


# ---------------------------------------------------------------------------
# AlertThrottle.reset
# ---------------------------------------------------------------------------

def test_manual_reset_clears_state():
    t = AlertThrottle(_policy(base_interval_seconds=60))
    t.allow("job_a", success=False)
    t.reset("job_a")
    assert t.allow("job_a", success=False) is True


def test_jobs_are_isolated():
    t = AlertThrottle(_policy(base_interval_seconds=60))
    t.allow("job_a", success=False)
    # job_b has its own fresh state
    assert t.allow("job_b", success=False) is True
