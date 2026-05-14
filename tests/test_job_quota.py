"""Tests for cronwatch.job_quota."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cronwatch.job_quota import (
    QuotaExceededError,
    QuotaPolicy,
    QuotaTracker,
)


def _utc(hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(2024, 1, 1, hour, minute, second, tzinfo=timezone.utc)


def _policy(**kwargs) -> QuotaPolicy:
    return QuotaPolicy(**kwargs)


def _tracker(**kwargs) -> QuotaTracker:
    return QuotaTracker(_policy(**kwargs))


# ---------------------------------------------------------------------------
# QuotaPolicy
# ---------------------------------------------------------------------------

def test_policy_default_unlimited():
    p = QuotaPolicy()
    assert p.max_runs_for("backup") == 0


def test_policy_per_job_override():
    p = QuotaPolicy(
        default_max_runs=10,
        per_job={"backup": {"max_runs": 3, "window_seconds": 600}},
    )
    assert p.max_runs_for("backup") == 3
    assert p.window_seconds_for("backup") == 600


def test_policy_falls_back_to_default_for_unknown_job():
    p = QuotaPolicy(default_max_runs=5, default_window_seconds=1800)
    assert p.max_runs_for("unknown") == 5
    assert p.window_seconds_for("unknown") == 1800


# ---------------------------------------------------------------------------
# QuotaTracker — unlimited
# ---------------------------------------------------------------------------

def test_unlimited_never_raises():
    tracker = _tracker(default_max_runs=0)
    for _ in range(100):
        tracker.check("job")
        tracker.record("job")


def test_unlimited_remaining_returns_none():
    tracker = _tracker(default_max_runs=0)
    assert tracker.remaining("job") is None


# ---------------------------------------------------------------------------
# QuotaTracker — limited
# ---------------------------------------------------------------------------

def test_first_run_allowed():
    tracker = _tracker(default_max_runs=3, default_window_seconds=3600)
    tracker.check("job", now=_utc(10))


def test_runs_within_limit_allowed():
    tracker = _tracker(default_max_runs=3, default_window_seconds=3600)
    base = _utc(10)
    for i in range(3):
        from datetime import timedelta
        ts = base.replace(minute=i)
        tracker.check("job", now=ts)
        tracker.record("job", now=ts)


def test_exceeding_limit_raises():
    tracker = _tracker(default_max_runs=2, default_window_seconds=3600)
    t1, t2 = _utc(10, 0), _utc(10, 1)
    tracker.record("job", now=t1)
    tracker.record("job", now=t2)
    with pytest.raises(QuotaExceededError) as exc_info:
        tracker.check("job", now=_utc(10, 2))
    assert exc_info.value.job_name == "job"
    assert exc_info.value.max_runs == 2


def test_old_runs_evicted_after_window():
    tracker = _tracker(default_max_runs=2, default_window_seconds=60)
    from datetime import timedelta
    early = _utc(10, 0)
    tracker.record("job", now=early)
    tracker.record("job", now=early)
    # Both timestamps are now outside the window
    later = _utc(10, 2)  # 120s later
    tracker.check("job", now=later)  # should not raise


def test_remaining_decrements_on_record():
    tracker = _tracker(default_max_runs=3, default_window_seconds=3600)
    now = _utc(10)
    assert tracker.remaining("job", now=now) == 3
    tracker.record("job", now=now)
    assert tracker.remaining("job", now=now) == 2
    tracker.record("job", now=now)
    assert tracker.remaining("job", now=now) == 1


def test_remaining_zero_when_quota_exhausted():
    tracker = _tracker(default_max_runs=1, default_window_seconds=3600)
    now = _utc(10)
    tracker.record("job", now=now)
    assert tracker.remaining("job", now=now) == 0


def test_per_job_quota_independent_of_other_jobs():
    p = QuotaPolicy(
        default_max_runs=100,
        per_job={"tight": {"max_runs": 1, "window_seconds": 3600}},
    )
    tracker = QuotaTracker(p)
    now = _utc(10)
    tracker.record("tight", now=now)
    with pytest.raises(QuotaExceededError):
        tracker.check("tight", now=now)
    # Other job is unaffected
    tracker.check("other", now=now)


def test_error_message_contains_job_name_and_limit():
    err = QuotaExceededError("myjob", 5, 3600)
    assert "myjob" in str(err)
    assert "5" in str(err)
