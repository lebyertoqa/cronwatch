"""Tests for cronwatch.changelog_reporter."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cronwatch.job_changelog import ChangelogEntry, ChangelogStore
from cronwatch.changelog_reporter import (
    build_changelog_report,
    ChangelogReport,
    ChangelogSummary,
)


def _utc(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


def _entry(job: str, field: str, day: int) -> ChangelogEntry:
    return ChangelogEntry(
        job_name=job,
        changed_at=_utc(2024, 1, day),
        field_name=field,
        old_value="old",
        new_value="new",
    )


@pytest.fixture()
def store(tmp_path):
    return ChangelogStore(str(tmp_path / "cl" / "changes.json"))


def test_empty_store_returns_empty_report(store):
    report = build_changelog_report(store)
    assert report.total_jobs_with_changes == 0
    assert report.total_changes == 0
    assert report.summaries == []


def test_single_job_single_change(store):
    store.record(_entry("backup", "schedule", 1))
    report = build_changelog_report(store)
    assert report.total_jobs_with_changes == 1
    assert report.total_changes == 1


def test_summary_for_known_job(store):
    store.record(_entry("backup", "schedule", 1))
    store.record(_entry("backup", "command", 2))
    report = build_changelog_report(store)
    summary = report.summary_for("backup")
    assert summary is not None
    assert summary.total_changes == 2
    assert set(summary.changed_fields) == {"schedule", "command"}


def test_summary_for_unknown_job_returns_none(store):
    store.record(_entry("backup", "schedule", 1))
    report = build_changelog_report(store)
    assert report.summary_for("nonexistent") is None


def test_last_changed_at_is_most_recent(store):
    store.record(_entry("backup", "schedule", 1))
    store.record(_entry("backup", "command", 5))
    store.record(_entry("backup", "timeout", 3))
    report = build_changelog_report(store)
    summary = report.summary_for("backup")
    assert summary.last_changed_at == _utc(2024, 1, 5)


def test_multiple_jobs_counted_separately(store):
    store.record(_entry("alpha", "schedule", 1))
    store.record(_entry("beta", "command", 2))
    store.record(_entry("beta", "timeout", 3))
    report = build_changelog_report(store)
    assert report.total_jobs_with_changes == 2
    assert report.total_changes == 3


def test_has_changes_true_when_entries_present(store):
    store.record(_entry("myjob", "schedule", 1))
    report = build_changelog_report(store)
    summary = report.summary_for("myjob")
    assert summary.has_changes is True


def test_changed_fields_deduplicated(store):
    store.record(_entry("myjob", "schedule", 1))
    store.record(_entry("myjob", "schedule", 2))
    report = build_changelog_report(store)
    summary = report.summary_for("myjob")
    assert summary.changed_fields == ["schedule"]
    assert summary.total_changes == 2
