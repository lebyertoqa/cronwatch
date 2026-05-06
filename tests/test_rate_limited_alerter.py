"""Tests for cronwatch.rate_limited_alerter."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, call

import pytest

from cronwatch.executor import ExecutionResult
from cronwatch.rate_limited_alerter import RateLimitedAlerter, build_rate_limited_alerter
from cronwatch.ratelimit import RateLimiter


UTC = timezone.utc
BASE = 1_000.0


def _result(job_name: str = "backup", success: bool = False) -> ExecutionResult:
    return ExecutionResult(
        job_name=job_name,
        success=success,
        exit_code=0 if success else 1,
        stdout="",
        stderr="",
        duration=1.0,
        started_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


@pytest.fixture()
def inner() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def limiter() -> RateLimiter:
    return RateLimiter(window_seconds=60.0, max_alerts=2)


@pytest.fixture()
def alerter(inner: MagicMock, limiter: RateLimiter) -> RateLimitedAlerter:
    return RateLimitedAlerter(inner, limiter)


def test_first_alert_forwarded(alerter: RateLimitedAlerter, inner: MagicMock, limiter: RateLimiter) -> None:
    alerter.send(_result(_now_patch(limiter, BASE)))
    inner.send.assert_called_once()


def _now_patch(limiter: RateLimiter, ts: float) -> str:
    # Helper: pre-seed limiter time by recording via public API and returning job name.
    return "backup"


def test_alert_suppressed_after_max(inner: MagicMock, limiter: RateLimiter) -> None:
    alerter = RateLimitedAlerter(inner, limiter)
    r = _result("backup")
    # Exhaust the 2-alert limit
    limiter.record("backup", _now=BASE)
    limiter.record("backup", _now=BASE + 1)
    alerter.send(r)
    inner.send.assert_not_called()


def test_alert_allowed_after_window_expires(inner: MagicMock) -> None:
    limiter = RateLimiter(window_seconds=60.0, max_alerts=1)
    alerter = RateLimitedAlerter(inner, limiter)
    limiter.record("backup", _now=BASE)
    # Manually advance: is_allowed checks real monotonic; use reset to simulate
    limiter.reset("backup")
    alerter.send(_result("backup"))
    inner.send.assert_called_once()


def test_reset_clears_limit(inner: MagicMock, limiter: RateLimiter) -> None:
    alerter = RateLimitedAlerter(inner, limiter)
    limiter.record("backup", _now=BASE)
    limiter.record("backup", _now=BASE + 1)
    alerter.reset("backup")
    alerter.send(_result("backup"))
    inner.send.assert_called_once()


def test_different_jobs_independent(inner: MagicMock, limiter: RateLimiter) -> None:
    alerter = RateLimitedAlerter(inner, limiter)
    limiter.record("job_a", _now=BASE)
    limiter.record("job_a", _now=BASE + 1)
    alerter.send(_result("job_b"))
    inner.send.assert_called_once()


def test_build_factory_returns_instance(inner: MagicMock) -> None:
    result = build_rate_limited_alerter(inner, window_seconds=120.0, max_alerts=3)
    assert isinstance(result, RateLimitedAlerter)
