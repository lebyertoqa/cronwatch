"""Tests for job_concurrency and concurrent_executor."""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest

from cronwatch.config import JobConfig
from cronwatch.executor import ExecutionResult
from cronwatch.job_concurrency import (
    ConcurrencyGuard,
    ConcurrencyPolicy,
    ConcurrencySlotUnavailable,
    build_concurrency_guard,
)
from cronwatch.concurrent_executor import ConcurrentExecutor


def _job(name: str = "test-job") -> JobConfig:
    return JobConfig(name=name, command="echo hi", schedule="* * * * *")


def _ok_result(job: JobConfig) -> ExecutionResult:
    return ExecutionResult(
        job_name=job.name, success=True, exit_code=0,
        stdout="ok", stderr="", duration=0.1,
    )


# ---------------------------------------------------------------------------
# ConcurrencyPolicy
# ---------------------------------------------------------------------------

def test_policy_returns_default_for_unknown_job():
    policy = ConcurrencyPolicy(default=3)
    assert policy.limit_for(_job("unknown")) == 3


def test_policy_returns_per_job_override():
    policy = ConcurrencyPolicy(default=1, per_job={"special": 4})
    assert policy.limit_for(_job("special")) == 4


def test_policy_falls_back_to_default_for_other_jobs():
    policy = ConcurrencyPolicy(default=2, per_job={"a": 5})
    assert policy.limit_for(_job("b")) == 2


# ---------------------------------------------------------------------------
# ConcurrencyGuard
# ---------------------------------------------------------------------------

def test_acquire_returns_true_when_slot_available():
    guard = build_concurrency_guard(default=2)
    job = _job()
    assert guard.acquire(job) is True
    guard.release(job)


def test_try_acquire_raises_when_no_slot():
    guard = build_concurrency_guard(default=1)
    job = _job()
    guard.acquire(job)  # exhaust the single slot
    with pytest.raises(ConcurrencySlotUnavailable) as exc_info:
        guard.try_acquire(job)
    assert exc_info.value.job_name == job.name
    guard.release(job)


def test_release_frees_slot_for_reuse():
    guard = build_concurrency_guard(default=1)
    job = _job()
    guard.acquire(job)
    guard.release(job)
    # Should not raise after release
    guard.try_acquire(job)
    guard.release(job)


def test_independent_jobs_do_not_share_semaphore():
    guard = build_concurrency_guard(default=1)
    job_a = _job("a")
    job_b = _job("b")
    guard.acquire(job_a)  # exhaust slot for a
    # b should still be acquirable
    assert guard.acquire(job_b) is True
    guard.release(job_a)
    guard.release(job_b)


# ---------------------------------------------------------------------------
# ConcurrentExecutor
# ---------------------------------------------------------------------------

def test_executor_runs_job_when_slot_available():
    job = _job()
    inner = MagicMock()
    inner.run.return_value = _ok_result(job)
    guard = build_concurrency_guard(default=1)
    executor = ConcurrentExecutor(inner=inner, guard=guard)

    result = executor.run(job)
    assert result.success is True
    inner.run.assert_called_once_with(job)


def test_executor_returns_failure_when_no_slot():
    job = _job()
    inner = MagicMock()
    guard = build_concurrency_guard(default=1)
    guard.acquire(job)  # exhaust slot

    executor = ConcurrentExecutor(inner=inner, guard=guard)
    result = executor.run(job)

    assert result.success is False
    assert result.exit_code == -1
    assert "concurrency limit" in result.stderr
    inner.run.assert_not_called()
    guard.release(job)


def test_executor_releases_slot_after_run():
    job = _job()
    inner = MagicMock()
    inner.run.return_value = _ok_result(job)
    guard = build_concurrency_guard(default=1)
    executor = ConcurrentExecutor(inner=inner, guard=guard)

    executor.run(job)
    # Slot should be free; acquiring again must succeed
    assert guard.acquire(job) is True
    guard.release(job)


def test_executor_releases_slot_even_on_exception():
    job = _job()
    inner = MagicMock()
    inner.run.side_effect = RuntimeError("boom")
    guard = build_concurrency_guard(default=1)
    executor = ConcurrentExecutor(inner=inner, guard=guard)

    with pytest.raises(RuntimeError):
        executor.run(job)

    # Slot must have been released
    assert guard.acquire(job) is True
    guard.release(job)
