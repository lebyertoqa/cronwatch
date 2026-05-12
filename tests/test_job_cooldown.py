"""Tests for cronwatch.job_cooldown."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from cronwatch.job_cooldown import CooldownPolicy, CooldownTracker


def _utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2024, 1, 1, hour, minute, tzinfo=timezone.utc)


def _job(name: str) -> MagicMock:
    j = MagicMock()
    j.name = name
    return j


# ---------------------------------------------------------------------------
# CooldownPolicy
# ---------------------------------------------------------------------------

def test_policy_returns_default_when_no_per_job():
    policy = CooldownPolicy(default_seconds=60)
    job = _job("backup")
    assert policy.seconds_for(job) == 60


def test_policy_returns_per_job_override():
    policy = CooldownPolicy(default_seconds=60, per_job={"backup": 300})
    job = _job("backup")
    assert policy.seconds_for(job) == 300


def test_policy_falls_back_for_unknown_job():
    policy = CooldownPolicy(default_seconds=30, per_job={"other": 120})
    job = _job("unknown")
    assert policy.seconds_for(job) == 30


# ---------------------------------------------------------------------------
# CooldownTracker — is_cooling_down
# ---------------------------------------------------------------------------

def test_no_completion_recorded_not_cooling_down():
    policy = CooldownPolicy(default_seconds=60)
    tracker = CooldownTracker(policy)
    job = _job("sync")
    assert tracker.is_cooling_down(job) is False


def test_zero_cooldown_never_cooling_down():
    policy = CooldownPolicy(default_seconds=0)
    tracker = CooldownTracker(policy)
    job = _job("sync")
    tracker.record_completion(job, at=_utc(10, 0))
    assert tracker.is_cooling_down(job, now=_utc(10, 0)) is False


def test_within_cooldown_window_is_cooling_down():
    policy = CooldownPolicy(default_seconds=300)
    tracker = CooldownTracker(policy)
    job = _job("report")
    tracker.record_completion(job, at=_utc(10, 0))
    # Only 2 minutes later — still cooling
    assert tracker.is_cooling_down(job, now=_utc(10, 2)) is True


def test_after_cooldown_window_not_cooling_down():
    policy = CooldownPolicy(default_seconds=300)
    tracker = CooldownTracker(policy)
    job = _job("report")
    tracker.record_completion(job, at=_utc(10, 0))
    # 6 minutes later — cooldown expired
    assert tracker.is_cooling_down(job, now=_utc(10, 6)) is False


# ---------------------------------------------------------------------------
# CooldownTracker — next_allowed
# ---------------------------------------------------------------------------

def test_next_allowed_none_when_no_completion():
    policy = CooldownPolicy(default_seconds=60)
    tracker = CooldownTracker(policy)
    assert tracker.next_allowed(_job("x")) is None


def test_next_allowed_none_when_zero_cooldown():
    policy = CooldownPolicy(default_seconds=0)
    tracker = CooldownTracker(policy)
    job = _job("x")
    tracker.record_completion(job, at=_utc(9, 0))
    assert tracker.next_allowed(job) is None


def test_next_allowed_returns_correct_datetime():
    policy = CooldownPolicy(default_seconds=120)
    tracker = CooldownTracker(policy)
    job = _job("deploy")
    completed_at = _utc(12, 0)
    tracker.record_completion(job, at=completed_at)
    expected = completed_at + timedelta(seconds=120)
    assert tracker.next_allowed(job) == expected


# ---------------------------------------------------------------------------
# CooldownTracker — reset
# ---------------------------------------------------------------------------

def test_reset_clears_cooldown_state():
    policy = CooldownPolicy(default_seconds=600)
    tracker = CooldownTracker(policy)
    job = _job("cleanup")
    tracker.record_completion(job, at=_utc(8, 0))
    tracker.reset(job)
    assert tracker.is_cooling_down(job, now=_utc(8, 1)) is False


def test_reset_unknown_job_does_not_raise():
    policy = CooldownPolicy(default_seconds=60)
    tracker = CooldownTracker(policy)
    tracker.reset(_job("nonexistent"))  # should not raise
