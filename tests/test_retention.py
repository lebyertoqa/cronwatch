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
# ---------------------------------------------------------------------------

def test_policy_applies_both_rules(store: HistoryStore) -> None:
    entries = [_entry("j", days_ago=d) for d in (20, 10, 2, 1, 0)]
    _seed(store, entries)
    policy = RetentionPolicy(store, max_age_days=5, max_entries=1)
    total = policy.apply("j")
    assert total >= 3
    assert len(store.get("j")) == 1


def test_policy_apply_all_covers_multiple_jobs(store: HistoryStore) -> None:
    for job in ("alpha", "beta"):
        _seed(store, [_entry(job, days_ago=d) for d in (30, 20, 1)])
    policy = RetentionPolicy(store, max_age_days=10)
    results = policy.apply_all()
    assert set(results.keys()) == {"alpha", "beta"}
    assert results["alpha"] == 2
    assert results["beta"] == 2
