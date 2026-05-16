"""Tests for job_profiling and profiling_reporter."""
from __future__ import annotations

import pytest

from cronwatch.job_profiling import DurationStats, ProfilingStore
from cronwatch.profiling_reporter import ProfilingReport, ProfilingReporter


@pytest.fixture
def store(tmp_path):
    return ProfilingStore(str(tmp_path))


@pytest.fixture
def reporter(store):
    return ProfilingReporter(store)


# ── DurationStats ──────────────────────────────────────────────────────────────

def test_stats_empty_returns_none_aggregates():
    s = DurationStats(job_name="backup")
    assert s.mean is None
    assert s.minimum is None
    assert s.maximum is None
    assert s.p95 is None
    assert s.count == 0


def test_stats_single_sample():
    s = DurationStats(job_name="backup", samples=[5.0])
    assert s.mean == 5.0
    assert s.minimum == 5.0
    assert s.maximum == 5.0
    assert s.p95 == 5.0


def test_stats_mean_multiple_samples():
    s = DurationStats(job_name="backup", samples=[2.0, 4.0, 6.0])
    assert s.mean == pytest.approx(4.0)


def test_stats_p95_picks_high_end():
    samples = list(range(1, 21))  # 1..20
    s = DurationStats(job_name="j", samples=[float(x) for x in samples])
    # 95th percentile of 20 samples → index 18 (0-based) → value 19
    assert s.p95 == pytest.approx(19.0)


def test_stats_min_max():
    s = DurationStats(job_name="j", samples=[10.0, 1.0, 5.0])
    assert s.minimum == 1.0
    assert s.maximum == 10.0


# ── ProfilingStore ─────────────────────────────────────────────────────────────

def test_store_record_and_retrieve(store):
    store.record("sync", 3.5)
    stats = store.stats_for("sync")
    assert stats.count == 1
    assert stats.mean == pytest.approx(3.5)


def test_store_multiple_records_accumulate(store):
    store.record("sync", 1.0)
    store.record("sync", 3.0)
    assert store.stats_for("sync").count == 2


def test_store_persists_across_instances(tmp_path):
    ProfilingStore(str(tmp_path)).record("job", 7.0)
    reloaded = ProfilingStore(str(tmp_path))
    assert reloaded.stats_for("job").count == 1


def test_store_all_job_names(store):
    store.record("a", 1.0)
    store.record("b", 2.0)
    assert set(store.all_job_names()) == {"a", "b"}


def test_store_clear_removes_job(store):
    store.record("x", 1.0)
    store.clear("x")
    assert store.stats_for("x").count == 0
    assert "x" not in store.all_job_names()


# ── ProfilingReporter ──────────────────────────────────────────────────────────

def test_reporter_build_report_empty(reporter):
    report = reporter.build_report()
    assert report.total_jobs == 0
    assert report.rows == []


def test_reporter_build_report_has_rows(store, reporter):
    store.record("alpha", 2.0)
    store.record("beta", 5.0)
    report = reporter.build_report()
    assert report.total_jobs == 2
    assert report.job_names() == ["alpha", "beta"]


def test_reporter_slow_jobs_filter(store, reporter):
    for _ in range(20):
        store.record("fast", 0.5)
        store.record("slow", 12.0)
    report = reporter.build_report()
    slow = report.slow_jobs(threshold_seconds=10.0)
    assert len(slow) == 1
    assert slow[0].job_name == "slow"


def test_reporter_report_for_single_job(store, reporter):
    store.record("nightly", 60.0)
    row = reporter.report_for_job("nightly")
    assert row.job_name == "nightly"
    assert row.count == 1
    assert row.mean == pytest.approx(60.0)
