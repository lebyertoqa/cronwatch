"""Tests for cronwatch.scheduler."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.alerting import Alerter
from cronwatch.config import AlertConfig, CronwatchConfig, JobConfig
from cronwatch.executor import ExecutionResult
from cronwatch.scheduler import Scheduler, is_due, next_run


# ── helpers ──────────────────────────────────────────────────────────────────

EVERY_MINUTE = "* * * * *"
NEVER_MATCH = "0 3 31 2 *"  # Feb 31 — practically never


def _make_config(*schedules: str) -> CronwatchConfig:
    jobs = [
        JobConfig(name=f"job{i}", command=f"echo {i}", schedule=s)
        for i, s in enumerate(schedules)
    ]
    return CronwatchConfig(jobs=jobs, alert=AlertConfig())


def _make_scheduler(*schedules: str) -> tuple[Scheduler, MagicMock]:
    alerter = MagicMock(spec=Alerter)
    return Scheduler(_make_config(*schedules), alerter), alerter


def _utc(year=2024, month=1, day=1, hour=12, minute=0, second=0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


# ── next_run / is_due ─────────────────────────────────────────────────────────

def test_next_run_returns_future_datetime():
    now = _utc()
    nxt = next_run(EVERY_MINUTE, now)
    assert nxt > now


def test_is_due_true_when_within_tolerance():
    # Exactly on the minute boundary — previous tick was 0 s ago
    now = _utc(second=0)
    assert is_due(EVERY_MINUTE, now, tolerance_seconds=30) is True


def test_is_due_false_when_outside_tolerance():
    # 45 s past the minute — outside default 30 s window
    now = _utc(second=45)
    assert is_due(EVERY_MINUTE, now, tolerance_seconds=30) is False


# ── Scheduler.tick ────────────────────────────────────────────────────────────

def test_tick_runs_due_job():
    scheduler, _ = _make_scheduler(EVERY_MINUTE)
    now = _utc(second=0)
    with patch("cronwatch.scheduler.run_job") as mock_run:
        mock_run.return_value = ExecutionResult(
            job_name="job0", success=True, returncode=0,
            stdout="", stderr="", duration=0.1,
        )
        results = scheduler.tick(now)
    assert len(results) == 1
    mock_run.assert_called_once()


def test_tick_skips_non_due_job():
    scheduler, _ = _make_scheduler(NEVER_MATCH)
    now = _utc(second=0)
    results = scheduler.tick(now)
    assert results == []


def test_tick_sends_alert_on_failure():
    scheduler, alerter = _make_scheduler(EVERY_MINUTE)
    now = _utc(second=0)
    failed = ExecutionResult(
        job_name="job0", success=False, returncode=1,
        stdout="", stderr="error", duration=0.5,
    )
    with patch("cronwatch.scheduler.run_job", return_value=failed):
        scheduler.tick(now)
    alerter.send.assert_called_once_with(failed)


def test_tick_no_alert_on_success():
    scheduler, alerter = _make_scheduler(EVERY_MINUTE)
    now = _utc(second=0)
    ok = ExecutionResult(
        job_name="job0", success=True, returncode=0,
        stdout="ok", stderr="", duration=0.1,
    )
    with patch("cronwatch.scheduler.run_job", return_value=ok):
        scheduler.tick(now)
    alerter.send.assert_not_called()


def test_tick_does_not_rerun_within_same_minute():
    scheduler, _ = _make_scheduler(EVERY_MINUTE)
    now = _utc(second=0)
    ok = ExecutionResult(
        job_name="job0", success=True, returncode=0,
        stdout="", stderr="", duration=0.05,
    )
    with patch("cronwatch.scheduler.run_job", return_value=ok) as mock_run:
        scheduler.tick(now)
        scheduler.tick(now)  # same timestamp — should not re-run
    assert mock_run.call_count == 1
