"""Tests for cronwatch.history."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronwatch.executor import ExecutionResult
from cronwatch.history import HistoryEntry, HistoryStore, _MAX_ENTRIES_PER_JOB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc(year: int = 2024, month: int = 1, day: int = 1) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


def _make_result(
    job_name: str = "backup",
    exit_code: int = 0,
    stdout: str = "ok",
    stderr: str = "",
) -> ExecutionResult:
    return ExecutionResult(
        job_name=job_name,
        exit_code=exit_code,
        succeeded=(exit_code == 0),
        stdout=stdout,
        stderr=stderr,
        duration_seconds=1.23,
        started_at=_utc(),
    )


@pytest.fixture()
def store(tmp_path: Path) -> HistoryStore:
    return HistoryStore(path=tmp_path / "history.json")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_record_creates_file(store: HistoryStore) -> None:
    store.record(_make_result())
    assert store.path.exists()


def test_record_and_retrieve(store: HistoryStore) -> None:
    store.record(_make_result(job_name="sync", exit_code=0))
    entries = store.get("sync")
    assert len(entries) == 1
    assert entries[0].job_name == "sync"
    assert entries[0].succeeded is True


def test_multiple_records_accumulate(store: HistoryStore) -> None:
    for _ in range(3):
        store.record(_make_result())
    assert len(store.get("backup")) == 3


def test_entries_pruned_to_max(store: HistoryStore) -> None:
    for _ in range(_MAX_ENTRIES_PER_JOB + 10):
        store.record(_make_result())
    assert len(store.get("backup")) == _MAX_ENTRIES_PER_JOB


def test_get_unknown_job_returns_empty(store: HistoryStore) -> None:
    assert store.get("nonexistent") == []


def test_last_failure_returns_none_on_all_success(store: HistoryStore) -> None:
    store.record(_make_result(exit_code=0))
    assert store.last_failure("backup") is None


def test_last_failure_returns_entry(store: HistoryStore) -> None:
    store.record(_make_result(exit_code=0))
    store.record(_make_result(exit_code=1, stderr="boom"))
    store.record(_make_result(exit_code=0))
    failure = store.last_failure("backup")
    assert failure is not None
    assert failure.exit_code == 1
    assert failure.stderr_tail == "boom"


def test_stdout_tail_truncated(store: HistoryStore) -> None:
    long_output = "x" * 1000
    store.record(_make_result(stdout=long_output))
    entry = store.get("backup")[0]
    assert len(entry.stdout_tail) == 500


def test_history_file_is_valid_json(store: HistoryStore) -> None:
    store.record(_make_result())
    with store.path.open() as fh:
        data = json.load(fh)
    assert isinstance(data, dict)


def test_entries_ordered_most_recent_last(store: HistoryStore) -> None:
    """Entries should be stored in insertion order (oldest first)."""
    store.record(_make_result(exit_code=0, stdout="first"))
    store.record(_make_result(exit_code=1, stdout="second"))
    store.record(_make_result(exit_code=0, stdout="third"))
    entries = store.get("backup")
    assert entries[0].stdout_tail == "first"
    assert entries[1].stdout_tail == "second"
    assert entries[2].stdout_tail == "third"
