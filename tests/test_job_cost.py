"""Tests for job_cost and cost_reporter modules."""
from __future__ import annotations

import pytest

from cronwatch.job_cost import CostEntry, CostPolicy, CostSummary, CostTracker
from cronwatch.cost_reporter import CostReport, CostReporter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _policy(**per_job) -> CostPolicy:
    return CostPolicy(default_cost_per_second=0.01, per_job=per_job)


@pytest.fixture()
def tracker() -> CostTracker:
    return CostTracker(policy=_policy(backup=0.05))


# ---------------------------------------------------------------------------
# CostPolicy
# ---------------------------------------------------------------------------


def test_policy_returns_default_for_unknown_job():
    policy = CostPolicy(default_cost_per_second=0.02)
    assert policy.rate_for("unknown") == 0.02


def test_policy_returns_per_job_rate():
    policy = CostPolicy(default_cost_per_second=0.01, per_job={"backup": 0.05})
    assert policy.rate_for("backup") == 0.05


def test_policy_falls_back_for_other_job():
    policy = CostPolicy(default_cost_per_second=0.01, per_job={"backup": 0.05})
    assert policy.rate_for("sync") == 0.01


# ---------------------------------------------------------------------------
# CostEntry
# ---------------------------------------------------------------------------


def test_entry_estimated_cost():
    entry = CostEntry(job_name="backup", duration_seconds=10.0, cost_per_second=0.05)
    assert entry.estimated_cost == pytest.approx(0.5)


def test_entry_zero_rate_zero_cost():
    entry = CostEntry(job_name="noop", duration_seconds=100.0, cost_per_second=0.0)
    assert entry.estimated_cost == 0.0


# ---------------------------------------------------------------------------
# CostTracker
# ---------------------------------------------------------------------------


def test_record_returns_entry(tracker):
    entry = tracker.record("backup", 20.0)
    assert isinstance(entry, CostEntry)
    assert entry.job_name == "backup"
    assert entry.duration_seconds == 20.0
    assert entry.cost_per_second == 0.05


def test_entries_for_filters_by_name(tracker):
    tracker.record("backup", 10.0)
    tracker.record("sync", 5.0)
    tracker.record("backup", 8.0)
    assert len(tracker.entries_for("backup")) == 2
    assert len(tracker.entries_for("sync")) == 1


def test_summarise_totals_correctly(tracker):
    tracker.record("backup", 10.0)  # 0.50
    tracker.record("backup", 20.0)  # 1.00
    summary = tracker.summarise("backup")
    assert summary.total_runs == 2
    assert summary.total_seconds == pytest.approx(30.0)
    assert summary.total_cost == pytest.approx(1.50)


def test_summarise_empty_job(tracker):
    summary = tracker.summarise("nonexistent")
    assert summary.total_runs == 0
    assert summary.total_cost == 0.0
    assert summary.average_cost is None


def test_average_cost(tracker):
    tracker.record("backup", 10.0)  # 0.50
    tracker.record("backup", 30.0)  # 1.50
    summary = tracker.summarise("backup")
    assert summary.average_cost == pytest.approx(1.00)


def test_total_cost_across_all_jobs(tracker):
    tracker.record("backup", 10.0)   # 0.50
    tracker.record("sync", 100.0)    # 1.00  (default 0.01)
    assert tracker.total_cost() == pytest.approx(1.50)


# ---------------------------------------------------------------------------
# CostReporter
# ---------------------------------------------------------------------------


def test_report_grand_total():
    t = CostTracker(policy=CostPolicy(default_cost_per_second=0.10))
    t.record("a", 5.0)   # 0.50
    t.record("b", 10.0)  # 1.00
    reporter = CostReporter(t)
    report = reporter.build_report()
    assert report.grand_total_cost == pytest.approx(1.50)


def test_report_most_expensive_job():
    t = CostTracker(policy=CostPolicy(default_cost_per_second=0.10))
    t.record("cheap", 1.0)
    t.record("expensive", 50.0)
    report = CostReporter(t).build_report()
    assert report.most_expensive_job is not None
    assert report.most_expensive_job.job_name == "expensive"


def test_report_empty_store():
    t = CostTracker(policy=CostPolicy())
    report = CostReporter(t).build_report()
    assert report.total_jobs == 0
    assert report.grand_total_cost == 0.0
    assert report.most_expensive_job is None
    assert report.cheapest_job is None


def test_report_jobs_above_threshold():
    t = CostTracker(policy=CostPolicy(default_cost_per_second=1.0))
    t.record("small", 0.5)   # 0.50
    t.record("large", 5.0)   # 5.00
    report = CostReporter(t).build_report()
    above = report.jobs_above_cost(1.0)
    assert len(above) == 1
    assert above[0].job_name == "large"
