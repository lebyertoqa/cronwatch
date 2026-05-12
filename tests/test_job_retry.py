"""Tests for cronwatch.job_retry."""
from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from cronwatch.config import JobConfig
from cronwatch.executor import ExecutionResult
from cronwatch.job_retry import (
    RetryPolicy,
    RetryResult,
    build_retry_policy,
    with_retry,
)


def _job(name: str = "backup") -> JobConfig:
    return JobConfig(name=name, command="echo hi", schedule="* * * * *")


def _ok(job: JobConfig) -> ExecutionResult:
    return ExecutionResult(job_name=job.name, success=True, exit_code=0,
                           stdout="ok", stderr="", duration=0.1)


def _fail(job: JobConfig) -> ExecutionResult:
    return ExecutionResult(job_name=job.name, success=False, exit_code=1,
                           stdout="", stderr="err", duration=0.1)


# ---------------------------------------------------------------------------
# RetryPolicy
# ---------------------------------------------------------------------------

def test_policy_defaults():
    p = RetryPolicy()
    assert p.attempts_for("any") == 1
    assert p.delay_for("any") == 5.0
    assert p.backoff_for("any") == 1.0


def test_policy_per_job_override():
    p = RetryPolicy(per_job={"backup": {"attempts": 3, "delay": 2.0, "backoff": 2.0}})
    assert p.attempts_for("backup") == 3
    assert p.delay_for("backup") == 2.0
    assert p.backoff_for("backup") == 2.0


def test_policy_falls_back_for_unknown_job():
    p = RetryPolicy(default_attempts=4, per_job={"other": {"attempts": 1}})
    assert p.attempts_for("unknown") == 4


# ---------------------------------------------------------------------------
# with_retry
# ---------------------------------------------------------------------------

def test_success_on_first_attempt_no_sleep():
    sleep = MagicMock()
    policy = RetryPolicy(default_attempts=3)
    result = with_retry(_job(), policy, _ok, sleep=sleep)

    assert result.succeeded is True
    assert result.attempts == 1
    sleep.assert_not_called()


def test_retries_on_failure_then_succeeds():
    sleep = MagicMock()
    policy = RetryPolicy(default_attempts=3, default_delay=1.0)
    calls = []

    def runner(job):
        calls.append(1)
        return _ok(job) if len(calls) >= 2 else _fail(job)

    result = with_retry(_job(), policy, runner, sleep=sleep)
    assert result.succeeded is True
    assert result.attempts == 2
    sleep.assert_called_once_with(1.0)


def test_exhausts_all_attempts_on_persistent_failure():
    sleep = MagicMock()
    policy = RetryPolicy(default_attempts=3, default_delay=2.0)
    result = with_retry(_job(), policy, _fail, sleep=sleep)

    assert result.succeeded is False
    assert result.attempts == 3
    assert sleep.call_count == 2


def test_backoff_multiplier_applied():
    sleep = MagicMock()
    policy = RetryPolicy(default_attempts=4, default_delay=1.0, default_backoff=2.0)
    with_retry(_job(), policy, _fail, sleep=sleep)

    assert sleep.call_args_list == [call(1.0), call(2.0), call(4.0)]


def test_single_attempt_no_sleep_on_failure():
    sleep = MagicMock()
    policy = RetryPolicy(default_attempts=1)
    result = with_retry(_job(), policy, _fail, sleep=sleep)

    assert result.succeeded is False
    assert result.attempts == 1
    sleep.assert_not_called()


def test_final_result_is_last_execution():
    policy = RetryPolicy(default_attempts=2)
    results = [
        ExecutionResult(job_name="backup", success=False, exit_code=1,
                        stdout="", stderr="first", duration=0.1),
        ExecutionResult(job_name="backup", success=False, exit_code=2,
                        stdout="", stderr="second", duration=0.2),
    ]
    it = iter(results)
    result = with_retry(_job(), policy, lambda _j: next(it), sleep=lambda _: None)
    assert result.final.exit_code == 2


# ---------------------------------------------------------------------------
# build_retry_policy
# ---------------------------------------------------------------------------

def test_build_retry_policy_from_dict():
    cfg = {"default_attempts": 5, "default_delay": 10.0, "default_backoff": 1.5,
           "per_job": {"sync": {"attempts": 2}}}
    p = build_retry_policy(cfg)
    assert p.default_attempts == 5
    assert p.default_delay == 10.0
    assert p.default_backoff == 1.5
    assert p.attempts_for("sync") == 2


def test_build_retry_policy_empty_dict():
    p = build_retry_policy({})
    assert p.default_attempts == 1
    assert p.default_delay == 5.0
    assert p.default_backoff == 1.0
