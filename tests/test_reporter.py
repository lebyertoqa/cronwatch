"""Tests for cronwatch.reporter."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatch.history import HistoryEntry
from cronwatch.reporter import JobSummary, generate_report, _summarise


def _utc(year=2024, month=1, day=1, hour=0, minute=0, second=0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


def _entry(job_name: str, exit_code: int, started_at: datetime, duration: float = 1.0) -> HistoryEntry:
    return HistoryEntry(
        job_name=job_name,
        started_at=started_at,
        exit_code=exit_code,
        duration_seconds=duration,
        stdout="",
        stderr="",
    )


def _make_store(data: dict) -> MagicMock:
    store = MagicMock()
    store.list_jobs.return_value = list(data.keys())
    store.get.side_effect = lambda name: data.get(name, [])
    return store


def test_summarise_empty_entries():
    summary = _summarise("myjob", [])
    assert summary.total_runs == 0
    assert summary.success_rate == 0.0
    assert summary.last_run is None
    assert summary.last_status is None


def test_summarise_all_successes():
    entries = [
        _entry("job", 0, _utc(hour=1), duration=2.0),
        _entry("job", 0, _utc(hour=2), duration=4.0),
    ]
    summary = _summarise("job", entries)
    assert summary.total_runs == 2
    assert summary.successful_runs == 2
    assert summary.failed_runs == 0
    assert summary.success_rate == 100.0
    assert summary.avg_duration_seconds == 3.0
    assert summary.last_status == "success"


def test_summarise_mixed_results():
    entries = [
        _entry("job", 0, _utc(hour=1)),
        _entry("job", 1, _utc(hour=2)),
        _entry("job", 1, _utc(hour=3)),
    ]
    summary = _summarise("job", entries)
    assert summary.total_runs == 3
    assert summary.successful_runs == 1
    assert summary.failed_runs == 2
    assert round(summary.success_rate, 2) == 33.33
    assert summary.last_status == "failure"
    assert summary.last_run == _utc(hour=3)


def test_success_rate_property():
    s = JobSummary("j", 4, 3, 1, None, "success", 1.0)
    assert s.success_rate == 75.0


def test_generate_report_uses_all_jobs():
    store = _make_store({
        "job_a": [_entry("job_a", 0, _utc(hour=1))],
        "job_b": [_entry("job_b", 1, _utc(hour=2))],
    })
    report = generate_report(store)
    assert report.total_jobs == 2
    names = [s.job_name for s in report.summaries]
    assert "job_a" in names
    assert "job_b" in names


def test_generate_report_filters_by_job_names():
    store = _make_store({
        "job_a": [_entry("job_a", 0, _utc(hour=1))],
        "job_b": [_entry("job_b", 1, _utc(hour=2))],
    })
    report = generate_report(store, job_names=["job_a"])
    assert report.total_jobs == 1
    assert report.summaries[0].job_name == "job_a"


def test_report_jobs_with_failures():
    store = _make_store({
        "ok_job": [_entry("ok_job", 0, _utc(hour=1))],
        "bad_job": [_entry("bad_job", 2, _utc(hour=2))],
    })
    report = generate_report(store)
    failing = report.jobs_with_failures
    assert len(failing) == 1
    assert failing[0].job_name == "bad_job"


def test_report_generated_at_is_utc():
    store = _make_store({})
    report = generate_report(store)
    assert report.generated_at.tzinfo == timezone.utc
