import time
import pytest

from cronwatch.config import JobConfig
from cronwatch.executor import ExecutionResult, run_job


def make_job(command: str, timeout: int = 30, name: str = "test-job") -> JobConfig:
    return JobConfig(name=name, command=command, schedule="* * * * *", timeout_seconds=timeout)


def test_successful_job_returns_success():
    job = make_job("echo hello")
    result = run_job(job)
    assert result.success is True
    assert result.exit_code == 0
    assert "hello" in result.stdout
    assert result.timed_out is False
    assert result.error is None


def test_failed_job_returns_failure():
    job = make_job("exit 1")
    result = run_job(job)
    assert result.success is False
    assert result.exit_code == 1
    assert result.timed_out is False


def test_result_has_correct_job_name():
    job = make_job("echo ok", name="my-job")
    result = run_job(job)
    assert result.job_name == "my-job"


def test_duration_is_positive():
    job = make_job("echo hi")
    result = run_job(job)
    assert result.duration_seconds > 0
    assert result.finished_at >= result.started_at


def test_stderr_captured():
    job = make_job("echo err >&2")
    result = run_job(job)
    assert "err" in result.stderr


def test_job_timeout():
    job = make_job("sleep 10", timeout=1)
    result = run_job(job)
    assert result.success is False
    assert result.timed_out is True
    assert result.exit_code == -1
    assert result.error is not None
    assert "timed out" in result.error


def test_invalid_command_returns_failure():
    job = make_job("/nonexistent_binary_xyz_abc")
    result = run_job(job)
    assert result.success is False


def test_execution_result_success_property():
    result = ExecutionResult(
        job_name="j",
        exit_code=0,
        stdout="",
        stderr="",
        duration_seconds=0.1,
        started_at=time.time(),
        finished_at=time.time(),
    )
    assert result.success is True

    result.exit_code = 1
    assert result.success is False

    result.exit_code = 0
    result.timed_out = True
    assert result.success is False

    result.timed_out = False
    result.error = "boom"
    assert result.success is False
