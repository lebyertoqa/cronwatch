"""Tests for cronwatch.group_reporter."""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import List

import pytest

from cronwatch.group_reporter import GroupReport, GroupSummary, build_group_report


def _utc(year: int = 2024, month: int = 1, day: int = 1, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def _job(name: str, schedule: str = "* * * * *") -> SimpleNamespace:
    return SimpleNamespace(name=name, schedule=schedule)


def _entry(job_name: str, success: bool, started_at: datetime | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        job_name=job_name,
        success=success,
        started_at=started_at or _utc(),
    )


# ---------------------------------------------------------------------------
# GroupSummary
# ---------------------------------------------------------------------------

def test_summary_success_rate_all_pass():
    s = GroupSummary(group_key="g", total=4, failures=0)
    assert s.success_rate == 1.0


def test_summary_success_rate_partial_failures():
    s = GroupSummary(group_key="g", total=4, failures=1)
    assert s.success_rate == pytest.approx(0.75)


def test_summary_success_rate_zero_total():
    s = GroupSummary(group_key="g", total=0, failures=0)
    assert s.success_rate == 1.0


def test_summary_has_failures_true():
    s = GroupSummary(group_key="g", total=2, failures=1)
    assert s.has_failures is True


def test_summary_has_failures_false():
    s = GroupSummary(group_key="g", total=2, failures=0)
    assert s.has_failures is False


# ---------------------------------------------------------------------------
# GroupReport
# ---------------------------------------------------------------------------

def test_worst_group_returns_key_with_lowest_success_rate():
    report = GroupReport(summaries={
        "good": GroupSummary(group_key="good", total=10, failures=0),
        "bad": GroupSummary(group_key="bad", total=10, failures=8),
    })
    assert report.worst_group() == "bad"


def test_worst_group_returns_none_when_empty():
    assert GroupReport().worst_group() is None


# ---------------------------------------------------------------------------
# build_group_report
# ---------------------------------------------------------------------------

def test_build_report_empty_entries():
    jobs = [_job("a", "@daily"), _job("b", "@daily")]
    report = build_group_report(jobs, [], lambda j: j.schedule)
    assert report.summaries["@daily"].total == 0
    assert report.summaries["@daily"].failures == 0


def test_build_report_counts_total_and_failures():
    jobs = [_job("a", "@daily"), _job("b", "@hourly")]
    entries = [
        _entry("a", success=True),
        _entry("a", success=False),
        _entry("b", success=True),
    ]
    report = build_group_report(jobs, entries, lambda j: j.schedule)
    assert report.summaries["@daily"].total == 2
    assert report.summaries["@daily"].failures == 1
    assert report.summaries["@hourly"].total == 1
    assert report.summaries["@hourly"].failures == 0


def test_build_report_ignores_unknown_job_entries():
    jobs = [_job("a", "@daily")]
    entries = [_entry("unknown_job", success=False)]
    report = build_group_report(jobs, entries, lambda j: j.schedule)
    assert report.summaries["@daily"].total == 0


def test_build_report_job_names_in_summary():
    jobs = [_job("a", "@daily"), _job("b", "@daily")]
    report = build_group_report(jobs, [], lambda j: j.schedule)
    assert set(report.summaries["@daily"].job_names) == {"a", "b"}


def test_build_report_success_rate_computed_correctly():
    jobs = [_job("a", "@daily")]
    entries = [_entry("a", True)] * 3 + [_entry("a", False)]
    report = build_group_report(jobs, entries, lambda j: j.schedule)
    assert report.summaries["@daily"].success_rate == pytest.approx(0.75)
