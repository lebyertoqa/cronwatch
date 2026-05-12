"""Tests for cronwatch.retrying_executor."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronwatch.config import JobConfig
from cronwatch.executor import ExecutionResult
from cronwatch.job_retry import RetryPolicy
from cronwatch.retrying_executor import RetryingExecutor, build_retrying_executor


def _job(name: str = "cleanup") -> JobConfig:
    return JobConfig(name=name, command="rm -rf /tmp/x", schedule="0 * * * *")


def _result(job: JobConfig, ok: bool, code: int = 0) -> ExecutionResult:
    return ExecutionResult(
        job_name=job.name, success=ok, exit_code=code,
        stdout="", stderr="", duration=0.05,
    )


def test_run_returns_retry_result_on_success():
    runner = MagicMock(side_effect=lambda j: _result(j, True))
    executor = RetryingExecutor(policy=RetryPolicy(default_attempts=3), runner=runner)
    rr = executor.run(_job())

    assert rr.succeeded is True
    assert rr.attempts == 1
    runner.assert_called_once()


def test_run_retries_on_failure():
    job = _job()
    responses = [_result(job, False, 1), _result(job, False, 1), _result(job, True, 0)]
    runner = MagicMock(side_effect=responses)
    policy = RetryPolicy(default_attempts=3, default_delay=0)
    executor = RetryingExecutor(policy=policy, runner=runner)
    rr = executor.run(job)

    assert rr.succeeded is True
    assert rr.attempts == 3
    assert runner.call_count == 3


def test_run_exhausts_attempts_returns_failure():
    job = _job()
    runner = MagicMock(side_effect=lambda j: _result(j, False, 1))
    policy = RetryPolicy(default_attempts=2, default_delay=0)
    executor = RetryingExecutor(policy=policy, runner=runner)
    rr = executor.run(job)

    assert rr.succeeded is False
    assert rr.attempts == 2


def test_build_retrying_executor_uses_cfg():
    cfg = {"default_attempts": 4, "default_delay": 0.0}
    executor = build_retrying_executor(cfg)
    assert executor.policy.default_attempts == 4


def test_build_retrying_executor_custom_runner():
    custom = MagicMock(return_value=_result(_job(), True))
    executor = build_retrying_executor({}, runner=custom)
    executor.run(_job())
    custom.assert_called_once()
