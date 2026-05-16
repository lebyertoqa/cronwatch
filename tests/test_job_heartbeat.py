"""Tests for cronwatch.job_heartbeat."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from cronwatch.job_heartbeat import HeartbeatEntry, HeartbeatStore


def _utc(year=2024, month=1, day=1, hour=12, minute=0, second=0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


@pytest.fixture
def store(tmp_path: Path) -> HeartbeatStore:
    return HeartbeatStore(str(tmp_path / "heartbeats"))


def test_get_returns_none_before_record(store: HeartbeatStore) -> None:
    assert store.get("backup") is None


def test_record_creates_entry(store: HeartbeatStore) -> None:
    ts = _utc()
    entry = store.record("backup", ts)
    assert entry.job_name == "backup"
    assert entry.last_success == ts


def test_get_returns_recorded_entry(store: HeartbeatStore) -> None:
    ts = _utc()
    store.record("backup", ts)
    retrieved = store.get("backup")
    assert retrieved is not None
    assert retrieved.job_name == "backup"
    assert retrieved.last_success == ts


def test_record_overwrites_previous(store: HeartbeatStore) -> None:
    t1 = _utc(hour=10)
    t2 = _utc(hour=11)
    store.record("backup", t1)
    store.record("backup", t2)
    assert store.get("backup").last_success == t2


def test_all_returns_all_entries(store: HeartbeatStore) -> None:
    store.record("job_a", _utc(hour=9))
    store.record("job_b", _utc(hour=10))
    all_entries = store.all()
    assert set(all_entries.keys()) == {"job_a", "job_b"}


def test_remove_deletes_entry(store: HeartbeatStore) -> None:
    store.record("cleanup", _utc())
    store.remove("cleanup")
    assert store.get("cleanup") is None


def test_remove_nonexistent_is_safe(store: HeartbeatStore) -> None:
    store.remove("ghost")  # should not raise


def test_entry_age_seconds(store: HeartbeatStore) -> None:
    ts = _utc(hour=10)
    entry = HeartbeatEntry(job_name="x", last_success=ts)
    now = _utc(hour=11)
    assert entry.age_seconds(now) == 3600.0


def test_entry_is_alive_within_ttl() -> None:
    ts = _utc(hour=10)
    entry = HeartbeatEntry(job_name="x", last_success=ts)
    now = _utc(hour=10, minute=30)
    assert entry.is_alive(ttl_seconds=3600, now=now) is True


def test_entry_is_not_alive_past_ttl() -> None:
    ts = _utc(hour=8)
    entry = HeartbeatEntry(job_name="x", last_success=ts)
    now = _utc(hour=10)
    assert entry.is_alive(ttl_seconds=3600, now=now) is False
