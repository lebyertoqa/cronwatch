"""Tests for SnapshotStore and SnapshotReporter."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronwatch.executor import ExecutionResult
from cronwatch.job_snapshot import Snapshot, SnapshotStore
from cronwatch.snapshot_reporter import SnapshotReporter


def _utc(year=2024, month=1, day=1, hour=0, minute=0, second=0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


def _result(name: str, exit_code: int, duration: float = 1.0) -> ExecutionResult:
    return ExecutionResult(
        job_name=name,
        command=f"run_{name}.sh",
        exit_code=exit_code,
        stdout="ok",
        stderr="",
        started_at=_utc(),
        duration=duration,
    )


@pytest.fixture
def store(tmp_path: Path) -> SnapshotStore:
    return SnapshotStore(tmp_path / "snapshots.json")


# ---------------------------------------------------------------------------
# SnapshotStore
# ---------------------------------------------------------------------------

def test_get_returns_none_before_any_record(store):
    assert store.get("myjob") is None


def test_record_success_stores_snapshot(store):
    store.record(_result("myjob", exit_code=0))
    snap = store.get("myjob")
    assert snap is not None
    assert snap.job_name == "myjob"
    assert snap.exit_code == 0


def test_record_failure_does_not_update_snapshot(store):
    store.record(_result("myjob", exit_code=0))
    store.record(_result("myjob", exit_code=1))
    snap = store.get("myjob")
    assert snap is not None
    assert snap.exit_code == 0  # still the good run


def test_snapshot_persists_across_reload(tmp_path):
    path = tmp_path / "snapshots.json"
    s1 = SnapshotStore(path)
    s1.record(_result("job_a", exit_code=0, duration=3.5))

    s2 = SnapshotStore(path)
    snap = s2.get("job_a")
    assert snap is not None
    assert snap.duration == pytest.approx(3.5)


def test_clear_removes_snapshot(store):
    store.record(_result("myjob", exit_code=0))
    store.clear("myjob")
    assert store.get("myjob") is None


def test_all_returns_all_snapshots(store):
    store.record(_result("job1", exit_code=0))
    store.record(_result("job2", exit_code=0))
    assert set(store.all().keys()) == {"job1", "job2"}


# ---------------------------------------------------------------------------
# SnapshotReporter
# ---------------------------------------------------------------------------

def test_analyse_returns_empty_when_all_succeed(store):
    store.record(_result("job1", exit_code=0))
    reporter = SnapshotReporter(store)
    reports = reporter.analyse([_result("job1", exit_code=0)])
    assert reports == []


def test_analyse_detects_regression(store):
    store.record(_result("job1", exit_code=0))
    reporter = SnapshotReporter(store)
    reports = reporter.analyse([_result("job1", exit_code=1)])
    assert len(reports) == 1
    assert reports[0].job_name == "job1"
    assert reports[0].is_regression is True


def test_analyse_no_regression_without_prior_success(store):
    reporter = SnapshotReporter(store)
    reports = reporter.analyse([_result("new_job", exit_code=1)])
    assert reports == []


def test_never_succeeded_lists_missing_jobs(store):
    store.record(_result("job_ok", exit_code=0))
    reporter = SnapshotReporter(store)
    result = reporter.never_succeeded(["job_ok", "job_new"])
    assert result == ["job_new"]


def test_last_good_age_returns_none_without_snapshot(store):
    reporter = SnapshotReporter(store)
    assert reporter.last_good_age_seconds("ghost") is None


def test_last_good_age_positive_after_record(store):
    store.record(_result("myjob", exit_code=0))
    reporter = SnapshotReporter(store)
    age = reporter.last_good_age_seconds("myjob")
    assert age is not None
    assert age >= 0
