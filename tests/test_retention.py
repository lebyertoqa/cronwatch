"""Tests for cronwatch.retention."""
from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone, timedelta

import pytest

from cronwatch.history import HistoryStore, HistoryEntry
from cronwatch.retention import prune_older_than, prune_excess, RetentionPolicy


def _utc(days_ago: float = 0) -> datetime:
    return datetime.now(tz=timezone.utc) - timedelta(days=days_ago)


def _entry(job: str, days_ago: float = 0, success: bool = True) -> HistoryEntry:
    t = _utc(days_ago)
    return HistoryEntry(
        job_name=job,
        started_at=t - timedelta(seconds=1),
        finished_at=t,
        exit_code=0 if success else 1,
        success=success,
        output="ok",
    )


@pytest.fixture()
def store(tmp_path: pathlib.Path) -> HistoryStore:
    s = HistoryStore(tmp_path / "history.json")
    return s


def _seed(store: HistoryStore, entries: list[HistoryEntry]) -> None:
    for e in entries:
        store.record(e)


# ---------------------------------------------------------------------------
# prune_older_than
# ---------------------------------------------------------------------------

def test_prune_older_than_removes_old_entries(store: HistoryStore) -> None:
    _seed(store, [_entry("j", days_ago=10), _entry("j", days_ago=5), _entry("j", days_ago=1)])
    cutoff = _utc(days_ago=3)
    removed = prune_older_than(store, "j", cutoff)
    assert removed == 2
    assert len(store.get("j")) == 1


def test_prune_older_than_keeps_all_when_none_old(store: HistoryStore) -> None:
    _seed(store, [_entry("j", days_ago=1), _entry("j", days_ago=0.5)])
    cutoff = _utc(days_ago=5)
    removed = prune_older_than(store, "j", cutoff)
    assert removed == 0
    assert len(store.get("j")) == 2


def test_prune_older_than_unknown_job_returns_zero(store: HistoryStore) -> None:
    removed = prune_older_than(store, "ghost", _utc())
    assert removed == 0


def test_prune_older_than_removes_all_entries(store: HistoryStore) -> None:
    """Pruning with a future cutoff should remove every entry for the job."""
    _seed(store, [_entry("j", days_ago=10), _entry("j", days_ago=5)])
    # cutoff is in the future relative to all entries
    cutoff = _utc(days_ago=-1)
    removed = prune_older_than(store, "j", cutoff)
    assert removed == 2
    assert store.get("j") == []


# ---------------------------------------------------------------------------
# prune_excess
# ---------------------------------------------------------------------------

def test_prune_excess_keeps_most_recent(store: HistoryStore) -> None:
    entries = [_entry("j", days_ago=d) for d in (10, 5, 3, 1, 0)]
    _seed(store, entries)
    removed = prune_excess(store, "j", max_entries=2)
    assert removed == 3
    remaining = store.get("j")
    assert len(remaining) == 2
    # The two kept entries should be the most recent
    assert all(e.finished_at >= _utc(days_ago=2) for e in remaining)


def test_prune_excess_no_op_when_under_limit(store: HistoryStore) -> None:
    _seed(store, [_entry("j"), _entry("j")])
    assert prune_excess(store, "j", max_entries=5) == 0


def test_prune_excess_invalid_max_raises(store: HistoryStore) -> None:
    with pytest.raises(ValueError):
        prune_excess(store, "j", max_entries=0)


# ---------------------------------------------------------------------------
# RetentionPolicy
# -------------------------------------------
