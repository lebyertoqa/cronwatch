"""Tests for cronwatch.job_status."""
from datetime import datetime, timezone

import pytest

from cronwatch.executor import ExecutionResult
from cronwatch.job_status import JobState, JobStatus, JobStatusRegistry


def _utc(year=2024, month=1, day=1, hour=0, minute=0, second=0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


def _ok(name: str = "job") -> ExecutionResult:
    return ExecutionResult(job_name=name, success=True, returncode=0,
                           stdout="", stderr="", duration=1.0)


def _fail(name: str = "job") -> ExecutionResult:
    return ExecutionResult(job_name=name, success=False, returncode=1,
                           stdout="", stderr="err", duration=1.0)


@pytest.fixture
def registry() -> JobStatusRegistry:
    return JobStatusRegistry()


def test_initial_state_is_idle(registry):
    status = registry.get("backup")
    assert status.state == JobState.IDLE


def test_mark_running_sets_state(registry):
    registry.mark_running("backup")
    assert registry.get("backup").state == JobState.RUNNING


def test_mark_running_records_started_at(registry):
    registry.mark_running("backup")
    assert registry.get("backup").last_started_at is not None


def test_mark_finished_success_sets_succeeded(registry):
    registry.mark_running("backup")
    registry.mark_finished("backup", _ok("backup"))
    assert registry.get("backup").state == JobState.SUCCEEDED


def test_mark_finished_failure_sets_failed(registry):
    registry.mark_running("backup")
    registry.mark_finished("backup", _fail("backup"))
    assert registry.get("backup").state == JobState.FAILED


def test_consecutive_failures_increments(registry):
    for _ in range(3):
        registry.mark_running("backup")
        registry.mark_finished("backup", _fail("backup"))
    assert registry.get("backup").consecutive_failures == 3


def test_success_resets_consecutive_failures(registry):
    registry.mark_running("backup")
    registry.mark_finished("backup", _fail("backup"))
    registry.mark_running("backup")
    registry.mark_finished("backup", _ok("backup"))
    assert registry.get("backup").consecutive_failures == 0


def test_is_healthy_when_idle(registry):
    assert registry.get("backup").is_healthy is True


def test_is_healthy_when_succeeded(registry):
    registry.mark_running("backup")
    registry.mark_finished("backup", _ok("backup"))
    assert registry.get("backup").is_healthy is True


def test_not_healthy_when_failed(registry):
    registry.mark_running("backup")
    registry.mark_finished("backup", _fail("backup"))
    assert registry.get("backup").is_healthy is False


def test_unhealthy_jobs_returns_only_failed(registry):
    registry.mark_running("a")
    registry.mark_finished("a", _ok("a"))
    registry.mark_running("b")
    registry.mark_finished("b", _fail("b"))
    unhealthy = registry.unhealthy_jobs()
    assert "b" in unhealthy
    assert "a" not in unhealthy


def test_reset_removes_entry(registry):
    registry.mark_running("backup")
    registry.reset("backup")
    assert "backup" not in registry.all_statuses()


def test_all_statuses_returns_all_tracked(registry):
    registry.mark_running("a")
    registry.mark_running("b")
    assert set(registry.all_statuses().keys()) == {"a", "b"}
