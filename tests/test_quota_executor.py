"""Tests for cronwatch.quota_executor."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

import pytest

from cronwatch.executor import ExecutionResult
from cronwatch.job_quota import QuotaPolicy, QuotaTracker
from cronwatch.quota_executor import QuotaExecutor, QuotaResult, build_quota_executor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@dataclass
class _FakeJob:
    name: str
    command: str = "echo hi"


class _FakeExecutor:
    def __init__(self, results: List[ExecutionResult]) -> None:
        self._results = iter(results)
        self.calls: List[str] = []

    def run(self, job) -> ExecutionResult:
        self.calls.append(job.name)
        return next(self._results)


def _ok(name: str = "job") -> ExecutionResult:
    return ExecutionResult(job_name=name, success=True, returncode=0,
                           stdout="", stderr="", duration=0.1)


def _fail(name: str = "job") -> ExecutionResult:
    return ExecutionResult(job_name=name, success=False, returncode=1,
                           stdout="", stderr="err", duration=0.1)


def _make_executor(
    results,
    max_runs: int = 0,
    window_seconds: int = 3600,
    per_job: dict | None = None,
) -> tuple[QuotaExecutor, _FakeExecutor]:
    policy = QuotaPolicy(
        default_max_runs=max_runs,
        default_window_seconds=window_seconds,
        per_job=per_job or {},
    )
    inner = _FakeExecutor(results)
    executor = QuotaExecutor(inner, QuotaTracker(policy))
    return executor, inner


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_unlimited_quota_always_runs():
    executor, inner = _make_executor([_ok(), _ok(), _ok()], max_runs=0)
    job = _FakeJob("job")
    for _ in range(3):
        r = executor.run(job)
        assert not r.quota_exceeded
        assert r.succeeded
    assert len(inner.calls) == 3


def test_first_run_within_quota_allowed():
    executor, inner = _make_executor([_ok()], max_runs=2)
    r = executor.run(_FakeJob("job"))
    assert not r.quota_exceeded
    assert r.result is not None


def test_quota_exceeded_skips_inner_executor():
    executor, inner = _make_executor([_ok(), _ok()], max_runs=1)
    job = _FakeJob("job")
    executor.run(job)  # consumes quota
    r = executor.run(job)
    assert r.quota_exceeded
    assert r.result is None
    assert len(inner.calls) == 1  # inner called only once


def test_quota_exceeded_result_not_succeeded():
    executor, _ = _make_executor([_ok()], max_runs=1)
    job = _FakeJob("job")
    executor.run(job)
    r = executor.run(job)
    assert not r.succeeded


def test_failed_run_not_counted_against_quota():
    # A failed execution should not consume quota
    executor, inner = _make_executor([_fail(), _ok()], max_runs=1)
    job = _FakeJob("job")
    r1 = executor.run(job)  # fails — quota not consumed
    assert not r1.quota_exceeded
    r2 = executor.run(job)  # should still be allowed
    assert not r2.quota_exceeded
    assert len(inner.calls) == 2


def test_per_job_quota_enforced_independently():
    policy = QuotaPolicy(
        default_max_runs=100,
        per_job={"tight": {"max_runs": 1, "window_seconds": 3600}},
    )
    inner = _FakeExecutor([_ok("tight"), _ok("other")])
    executor = QuotaExecutor(inner, QuotaTracker(policy))
    executor.run(_FakeJob("tight"))
    r = executor.run(_FakeJob("tight"))
    assert r.quota_exceeded
    r2 = executor.run(_FakeJob("other"))
    assert not r2.quota_exceeded


def test_build_quota_executor_returns_quota_executor():
    inner = _FakeExecutor([_ok()])
    ex = build_quota_executor(inner)
    assert isinstance(ex, QuotaExecutor)


def test_quota_result_job_name_set_on_exceeded():
    executor, _ = _make_executor([_ok()], max_runs=1)
    job = _FakeJob("myjob")
    executor.run(job)
    r = executor.run(job)
    assert r.job_name == "myjob"
