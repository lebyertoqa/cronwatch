"""Tests for cronwatch.notifier."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from cronwatch.executor import ExecutionResult
from cronwatch.notifier import Notifier


def _make_result(job_name: str = "backup", success: bool = False, exit_code: int = 1) -> ExecutionResult:
    return ExecutionResult(
        job_name=job_name,
        success=success,
        exit_code=exit_code if not success else 0,
        stdout="",
        stderr="",
        duration=1.0,
    )


def test_failed_job_triggers_first_notification():
    notifier = Notifier(min_interval_seconds=3600)
    result = _make_result(success=False)
    assert notifier.should_notify(result) is True


def test_second_failure_within_interval_suppressed():
    notifier = Notifier(min_interval_seconds=3600)
    result = _make_result(success=False)
    notifier.should_notify(result)  # first — allowed
    assert notifier.should_notify(result) is False  # second — suppressed


def test_failure_after_interval_allowed():
    notifier = Notifier(min_interval_seconds=10)
    result = _make_result(success=False)
    notifier.should_notify(result)

    with patch("cronwatch.notifier.time.monotonic", return_value=time.monotonic() + 20):
        assert notifier.should_notify(result) is True


def test_success_does_not_notify_when_no_prior_failure():
    notifier = Notifier(notify_on_recovery=True)
    result = _make_result(success=True)
    assert notifier.should_notify(result) is False


def test_recovery_notifies_when_enabled():
    notifier = Notifier(notify_on_recovery=True)
    fail = _make_result(success=False)
    ok = _make_result(success=True)
    notifier.should_notify(fail)
    assert notifier.should_notify(ok) is True


def test_recovery_suppressed_when_disabled():
    notifier = Notifier(notify_on_recovery=False)
    fail = _make_result(success=False)
    ok = _make_result(success=True)
    notifier.should_notify(fail)
    assert notifier.should_notify(ok) is False


def test_consecutive_failures_tracked():
    notifier = Notifier(min_interval_seconds=0)
    result = _make_result(success=False)
    notifier.should_notify(result)
    notifier.should_notify(result)
    notifier.should_notify(result)
    assert notifier.consecutive_failures("backup") == 3


def test_consecutive_failures_reset_on_success():
    notifier = Notifier(min_interval_seconds=0)
    fail = _make_result(success=False)
    ok = _make_result(success=True)
    notifier.should_notify(fail)
    notifier.should_notify(fail)
    notifier.should_notify(ok)
    assert notifier.consecutive_failures("backup") == 0


def test_reset_clears_state():
    notifier = Notifier(min_interval_seconds=3600)
    result = _make_result(success=False)
    notifier.should_notify(result)  # sets last_notified_at
    notifier.reset("backup")
    # After reset, next failure should be allowed again
    assert notifier.should_notify(result) is True


def test_independent_state_per_job():
    notifier = Notifier(min_interval_seconds=3600)
    r1 = _make_result(job_name="job_a", success=False)
    r2 = _make_result(job_name="job_b", success=False)
    notifier.should_notify(r1)
    # job_b has its own state — should still notify
    assert notifier.should_notify(r2) is True
