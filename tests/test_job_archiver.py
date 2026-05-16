"""Tests for cronwatch.job_archiver."""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cronwatch.job_archiver import ArchivePolicy, ArchiveStore, JobArchiver
from cronwatch.history import HistoryEntry, HistoryStore


def _utc(**kwargs) -> datetime:
    return datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(**kwargs)


def _entry(
    job_name: str = "backup",
    success: bool = True,
    finished_days_ago: int = 0,
) -> HistoryEntry:
    finished = _utc() - timedelta(days=finished_days_ago)
    started = finished - timedelta(seconds=5)
    return HistoryEntry(
        job_name=job_name,
        success=success,
        exit_code=0 if success else 1,
        duration=5.0,
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
    )


@pytest.fixture()
def dirs(tmp_path: Path):
    return tmp_path / "history", tmp_path / "archive"


@pytest.fixture()
def history(dirs):
    return HistoryStore(dirs[0])


@pytest.fixture()
def archive(dirs):
    return ArchiveStore(dirs[1])


# --- ArchivePolicy ---

def test_policy_should_archive_old_entry():
    policy = ArchivePolicy(older_than_days=30)
    entry = _entry(finished_days_ago=31)
    assert policy.should_archive(entry, now=_utc()) is True


def test_policy_should_not_archive_recent_entry():
    policy = ArchivePolicy(older_than_days=30)
    entry = _entry(finished_days_ago=10)
    assert policy.should_archive(entry, now=_utc()) is False


def test_policy_boundary_exactly_at_limit():
    policy = ArchivePolicy(older_than_days=30)
    entry = _entry(finished_days_ago=30)
    # exactly 30 days is NOT strictly greater than threshold
    assert policy.should_archive(entry, now=_utc()) is False


def test_policy_no_finished_at_never_archived():
    policy = ArchivePolicy(older_than_days=1)
    entry = _entry(finished_days_ago=100)
    entry.finished_at = None
    assert policy.should_archive(entry, now=_utc()) is False


# --- ArchiveStore ---

def test_archive_store_append_and_retrieve(archive):
    entry = _entry(job_name="cleanup")
    archive.append(entry)
    result = archive.entries_for("cleanup")
    assert len(result) == 1
    assert result[0].job_name == "cleanup"


def test_archive_store_empty_for_unknown_job(archive):
    assert archive.entries_for("nonexistent") == []


def test_archive_store_multiple_entries(archive):
    for i in range(3):
        archive.append(_entry(job_name="sync", finished_days_ago=i + 40))
    assert len(archive.entries_for("sync")) == 3


# --- JobArchiver ---

def test_archiver_moves_old_entries(history, archive):
    old = _entry(finished_days_ago=60)
    recent = _entry(finished_days_ago=5)
    # seed history manually via replace_entries
    history.replace_entries("backup", [old, recent])
    policy = ArchivePolicy(older_than_days=30)
    archiver = JobArchiver(history, archive, policy)
    count = archiver.archive_job("backup", now=_utc())
    assert count == 1
    assert len(archive.entries_for("backup")) == 1
    assert len(history.entries_for("backup")) == 1


def test_archiver_no_entries_to_archive(history, archive):
    recent = _entry(finished_days_ago=2)
    history.replace_entries("backup", [recent])
    archiver = JobArchiver(history, archive)
    count = archiver.archive_job("backup", now=_utc())
    assert count == 0
    assert len(history.entries_for("backup")) == 1


def test_archiver_all_entries_archived(history, archive):
    entries = [_entry(finished_days_ago=50), _entry(finished_days_ago=60)]
    history.replace_entries("backup", entries)
    archiver = JobArchiver(history, archive, ArchivePolicy(older_than_days=30))
    count = archiver.archive_job("backup", now=_utc())
    assert count == 2
    assert history.entries_for("backup") == []
    assert len(archive.entries_for("backup")) == 2


def test_archiver_unknown_job_returns_zero(history, archive):
    archiver = JobArchiver(history, archive)
    assert archiver.archive_job("ghost", now=_utc()) == 0
