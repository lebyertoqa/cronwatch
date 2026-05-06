"""Tests for job_timeout and timed_executor."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.config import JobConfig
from cronwatch.executor import ExecutionResult
from cronwatch.job_timeout import JobTimeoutError, TimeoutPolicy, enforce_timeout
from cronwatch.timed_executor import TimedExecutor, build_timed_executor


# ---------------------------------------------------------------------------
# TimeoutPolicy
# ---------------------------------------------------------------------------

def test_policy_returns_default_when_no_per_job():
    policy = TimeoutPolicy(default_seconds=60)
    assert policy.timeout_for("backup") == 60


def test_policy_returns_per_job_override():
    policy = TimeoutPolicy(default_seconds=60, per_job={"slow_job": 300})
    assert policy.timeout_for("slow_job") == 300


def test_policy_falls_back_to_default_for_unknown_job():
    policy = TimeoutPolicy(default_seconds=120, per_job={"other": 10})
    assert policy.timeout_for("unknown") == 120


# ---------------------------------------------------------------------------
# enforce_timeout context manager
# ---------------------------------------------------------------------------

def test_no_timeout_when_zero_seconds():
    """A timeout of 0 disables enforcement entirely."""
    called = []
    with enforce_timeout("job", 0):
        called.append(True)
    assert called == [True]


def test_block_completes_before_deadline():
    with enforce_timeout("quick", 5):
        time.sleep(0.01)  # well within budget


def test_job_timeout_error_message():
    exc = JobTimeoutError("my_job", 30)
    assert "my_job" in str(exc)
    assert "30" in str(exc)
    assert exc.job_name == "my_job"
    assert exc.timeout_seconds == 30


# ---------------------------------------------------------------------------
# TimedExecutor
# ---------------------------------------------------------------------------

def _make_job(name: str = "test_job", command: str = "echo hi") -> JobConfig:
    return JobConfig(name=name, command=command, schedule="* * * * *")


def _ok_result(job_name: str = "test_job") -> ExecutionResult:
    return ExecutionResult(
        job_name=job_name, success=True, exit_code=0,
        stdout="ok", stderr="", duration=0.1,
    )


def test_timed_executor_returns_result_on_success():
    job = _make_job()
    with patch("cronwatch.timed_executor.run_job", return_value=_ok_result()) as mock_run:
        executor = build_timed_executor(default_seconds=60)
        result = executor.run(job)
    mock_run.assert_called_once_with(job)
    assert result.success is True


def test_timed_executor_returns_failure_on_timeout():
    job = _make_job(name="slow")
    policy = TimeoutPolicy(default_seconds=10)
    executor = TimedExecutor(policy)

    with patch("cronwatch.timed_executor.run_job") as mock_run, \
         patch("cronwatch.timed_executor.enforce_timeout") as mock_ctx:
        # Simulate enforce_timeout raising JobTimeoutError
        mock_ctx.return_value.__enter__ = MagicMock(
            side_effect=JobTimeoutError("slow", 10)
        )
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

        # Patch enforce_timeout to raise directly
        with patch("cronwatch.timed_executor.enforce_timeout",
                   side_effect=JobTimeoutError("slow", 10)):
            result = executor.run(job)

    assert result.success is False
    assert result.exit_code == -1
    assert "slow" in result.stderr


def test_timed_executor_uses_per_job_timeout():
    job = _make_job(name="special")
    policy = TimeoutPolicy(default_seconds=60, per_job={"special": 5})
    executor = TimedExecutor(policy)

    with patch("cronwatch.timed_executor.run_job", return_value=_ok_result("special")), \
         patch("cronwatch.timed_executor.enforce_timeout") as mock_ctx:
        mock_ctx.return_value.__enter__ = MagicMock(return_value=None)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        executor.run(job)
        mock_ctx.assert_called_once_with("special", 5)
