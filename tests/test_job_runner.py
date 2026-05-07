"""Tests for cronwatch.job_runner."""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.config import JobConfig
from cronwatch.executor import ExecutionResult
from cronwatch.job_lock import LockAcquisitionError
from cronwatch.job_runner import JobRunner, RunnerResult, build_job_runner
from cronwatch.job_timeout import TimeoutPolicy


def _job(name: str = "test-job", command: str = "echo hi") -> JobConfig:
    return JobConfig(name=name, command=command, schedule="* * * * *")


def _ok_result(name: str = "test-job", duration: float = 0.1) -> ExecutionResult:
    return ExecutionResult(
        job_name=name,
        success=True,
        exit_code=0,
        stdout="ok",
        stderr="",
        duration=duration,
        started_at=__import__("datetime").datetime.utcnow(),
    )


@pytest.fixture()
def lock_dir(tmp_path: Path) -> str:
    d = tmp_path / "locks"
    d.mkdir()
    return str(d)


@pytest.fixture()
def runner(lock_dir: str) -> JobRunner:
    return build_job_runner(lock_dir=lock_dir)


def test_successful_run_returns_result(runner: JobRunner) -> None:
    with patch("cronwatch.job_runner.run_job", return_value=_ok_result()) as mock_run:
        outcome = runner.run(_job())
    assert not outcome.skipped
    assert outcome.result is not None
    assert outcome.result.success
    mock_run.assert_called_once()


def test_lock_held_causes_skip(lock_dir: str) -> None:
    runner = build_job_runner(lock_dir=lock_dir)
    job = _job()
    with patch(
        "cronwatch.job_runner.JobLock.acquire",
        side_effect=LockAcquisitionError("already locked"),
    ):
        outcome = runner.run(job)
    assert outcome.skipped
    assert "already locked" in outcome.skip_reason
    assert outcome.result is None


def test_lock_released_after_run(runner: JobRunner, lock_dir: str) -> None:
    job = _job(name="lock-test")
    with patch("cronwatch.job_runner.run_job", return_value=_ok_result("lock-test")):
        runner.run(job)
    lock_files = list(Path(lock_dir).glob("*.lock"))
    assert lock_files == [], "Lock file should be removed after run"


def test_timeout_exceeded_marks_failure(lock_dir: str) -> None:
    policy = TimeoutPolicy(default_seconds=1, per_job={"slow-job": 1})
    runner = build_job_runner(lock_dir=lock_dir, timeout_policy=policy)
    slow = _ok_result(name="slow-job", duration=5.0)
    with patch("cronwatch.job_runner.run_job", return_value=slow):
        outcome = runner.run(_job(name="slow-job"))
    assert outcome.result is not None
    assert not outcome.result.success
    assert "timed out" in outcome.result.stderr


def test_within_timeout_stays_success(lock_dir: str) -> None:
    policy = TimeoutPolicy(default_seconds=10)
    runner = build_job_runner(lock_dir=lock_dir, timeout_policy=policy)
    fast = _ok_result(duration=0.5)
    with patch("cronwatch.job_runner.run_job", return_value=fast):
        outcome = runner.run(_job())
    assert outcome.result is not None
    assert outcome.result.success


def test_auditing_executor_used_when_provided(lock_dir: str) -> None:
    mock_executor = MagicMock()
    mock_executor.run.return_value = _ok_result()
    runner = build_job_runner(lock_dir=lock_dir, auditing_executor=mock_executor)
    outcome = runner.run(_job())
    mock_executor.run.assert_called_once()
    assert not outcome.skipped
