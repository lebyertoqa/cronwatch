"""Tests for cronwatch.job_suppression."""
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from cronwatch.job_suppression import SuppressionEntry, SuppressionStore


def _utc(**kwargs) -> datetime:
    return datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(**kwargs)


@pytest.fixture
def store(tmp_path: Path) -> SuppressionStore:
    return SuppressionStore(tmp_path / "suppressions.json")


def test_entry_active_when_no_expiry():
    e = SuppressionEntry("backup", "maintenance", _utc().isoformat(), expires_at=None)
    assert e.is_active() is True
    assert e.is_expired() is False


def test_entry_expired_when_past_expiry():
    e = SuppressionEntry(
        "backup", "maintenance",
        _utc().isoformat(),
        expires_at=_utc(hours=-1).isoformat(),
    )
    assert e.is_expired(now=_utc()) is True
    assert e.is_active(now=_utc()) is False


def test_entry_not_expired_before_expiry():
    e = SuppressionEntry(
        "backup", "maintenance",
        _utc().isoformat(),
        expires_at=_utc(hours=2).isoformat(),
    )
    assert e.is_expired(now=_utc()) is False
    assert e.is_active(now=_utc()) is True


def test_suppress_creates_entry(store: SuppressionStore):
    entry = store.suppress("myjob", "planned downtime", now=_utc())
    assert entry.job_name == "myjob"
    assert entry.reason == "planned downtime"
    assert entry.expires_at is None


def test_is_suppressed_returns_true_after_suppress(store: SuppressionStore):
    store.suppress("myjob", "reason", now=_utc())
    assert store.is_suppressed("myjob", now=_utc()) is True


def test_is_suppressed_returns_false_for_unknown_job(store: SuppressionStore):
    assert store.is_suppressed("unknown", now=_utc()) is False


def test_release_removes_suppression(store: SuppressionStore):
    store.suppress("myjob", "reason", now=_utc())
    released = store.release("myjob")
    assert released is True
    assert store.is_suppressed("myjob", now=_utc()) is False


def test_release_returns_false_when_not_suppressed(store: SuppressionStore):
    assert store.release("ghost") is False


def test_expired_suppression_not_active(store: SuppressionStore):
    store.suppress("myjob", "reason", expires_at=_utc(hours=1), now=_utc())
    future = _utc(hours=2)
    assert store.is_suppressed("myjob", now=future) is False


def test_active_suppressions_excludes_expired(store: SuppressionStore):
    store.suppress("job1", "r1", expires_at=_utc(hours=1), now=_utc())
    store.suppress("job2", "r2", now=_utc())  # indefinite
    future = _utc(hours=2)
    active = store.active_suppressions(now=future)
    assert len(active) == 1
    assert active[0].job_name == "job2"


def test_purge_expired_removes_expired_entries(store: SuppressionStore):
    store.suppress("job1", "r1", expires_at=_utc(hours=1), now=_utc())
    store.suppress("job2", "r2", expires_at=_utc(hours=3), now=_utc())
    removed = store.purge_expired(now=_utc(hours=2))
    assert removed == 1
    assert store.is_suppressed("job2", now=_utc(hours=2)) is True


def test_suppress_persists_across_store_instances(tmp_path: Path):
    path = tmp_path / "suppressions.json"
    s1 = SuppressionStore(path)
    s1.suppress("myjob", "reason", now=_utc())
    s2 = SuppressionStore(path)
    assert s2.is_suppressed("myjob", now=_utc()) is True
