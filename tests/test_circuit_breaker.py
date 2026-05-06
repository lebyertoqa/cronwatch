"""Tests for cronwatch.circuit_breaker."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from cronwatch.circuit_breaker import CircuitBreaker


def _utc(offset_seconds: float = 0) -> datetime:
    return datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(
        seconds=offset_seconds
    )


@pytest.fixture()
def cb() -> CircuitBreaker:
    return CircuitBreaker(threshold=3, recovery_window=300)


def test_initial_state_closed(cb):
    assert not cb.is_open("myjob")


def test_failures_below_threshold_stay_closed(cb):
    cb.record_failure("myjob")
    cb.record_failure("myjob")
    assert not cb.is_open("myjob")


def test_threshold_failures_open_breaker(cb):
    with patch("cronwatch.circuit_breaker._utcnow", return_value=_utc()):
        for _ in range(3):
            cb.record_failure("myjob")
        assert cb.is_open("myjob")


def test_success_closes_breaker(cb):
    with patch("cronwatch.circuit_breaker._utcnow", return_value=_utc()):
        for _ in range(3):
            cb.record_failure("myjob")
    cb.record_success("myjob")
    assert not cb.is_open("myjob")


def test_success_resets_consecutive_count(cb):
    cb.record_failure("myjob")
    cb.record_failure("myjob")
    cb.record_success("myjob")
    assert cb.consecutive_failures("myjob") == 0


def test_open_breaker_closed_after_recovery_window(cb):
    open_time = _utc(0)
    after_recovery = _utc(301)
    with patch("cronwatch.circuit_breaker._utcnow", return_value=open_time):
        for _ in range(3):
            cb.record_failure("myjob")
    with patch("cronwatch.circuit_breaker._utcnow", return_value=after_recovery):
        assert not cb.is_open("myjob")


def test_open_breaker_still_open_before_recovery_window(cb):
    open_time = _utc(0)
    before_recovery = _utc(100)
    with patch("cronwatch.circuit_breaker._utcnow", return_value=open_time):
        for _ in range(3):
            cb.record_failure("myjob")
    with patch("cronwatch.circuit_breaker._utcnow", return_value=before_recovery):
        assert cb.is_open("myjob")


def test_reset_closes_breaker_immediately(cb):
    with patch("cronwatch.circuit_breaker._utcnow", return_value=_utc()):
        for _ in range(3):
            cb.record_failure("myjob")
    cb.reset("myjob")
    assert not cb.is_open("myjob")
    assert cb.consecutive_failures("myjob") == 0


def test_multiple_jobs_are_independent(cb):
    with patch("cronwatch.circuit_breaker._utcnow", return_value=_utc()):
        for _ in range(3):
            cb.record_failure("job_a")
    assert cb.is_open("job_a")
    assert not cb.is_open("job_b")
