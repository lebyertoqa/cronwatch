"""Tests for cronwatch.job_mute."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from cronwatch.job_mute import MuteEntry, MuteStore


def _utc(year=2024, month=1, day=1, hour=0, minute=0, second=0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


@pytest.fixture
def store(tmp_path):
    return MuteStore(str(tmp_path / "mutes.json"))


def test_entry_indefinite_when_no_muted_until():
    e = MuteEntry(job_name="j", muted_at=_utc(), muted_until=None)
    assert e.is_indefinite() is True


def test_entry_not_indefinite_when_muted_until_set():
    e = MuteEntry(job_name="j", muted_at=_utc(), muted_until=_utc(hour=2))
    assert e.is_indefinite() is False


def test_entry_active_when_indefinite():
    e = MuteEntry(job_name="j", muted_at=_utc(), muted_until=None)
    assert e.is_active(now=_utc(year=2099)) is True


def test_entry_active_before_muted_until():
    future = _utc(hour=5)
    e = MuteEntry(job_name="j", muted_at=_utc(), muted_until=future)
    assert e.is_active(now=_utc(hour=3)) is True


def test_entry_inactive_after_muted_until():
    past = _utc(hour=1)
    e = MuteEntry(job_name="j", muted_at=_utc(), muted_until=past)
    assert e.is_active(now=_utc(hour=3)) is False


def test_roundtrip_serialisation():
    e = MuteEntry(
        job_name="backup",
        muted_at=_utc(),
        muted_until=_utc(hour=8),
        reason="maintenance",
    )
    assert MuteEntry.from_dict(e.to_dict()) == e


def test_roundtrip_indefinite_serialisation():
    e = MuteEntry(job_name="backup", muted_at=_utc(), muted_until=None)
    restored = MuteEntry.from_dict(e.to_dict())
    assert restored.muted_until is None


def test_get_returns_none_before_any_mute(store):
    assert store.get("nojob") is None


def test_mute_and_retrieve(store):
    e = MuteEntry(job_name="job1", muted_at=_utc(), muted_until=None)
    store.mute(e)
    retrieved = store.get("job1")
    assert retrieved is not None
    assert retrieved.job_name == "job1"


def test_is_muted_returns_true_for_active_entry(store):
    future = _utc(year=2099)
    e = MuteEntry(job_name="job2", muted_at=_utc(), muted_until=future)
    store.mute(e)
    assert store.is_muted("job2", now=_utc()) is True


def test_is_muted_returns_false_for_expired_entry(store):
    past = _utc(hour=1)
    e = MuteEntry(job_name="job3", muted_at=_utc(), muted_until=past)
    store.mute(e)
    assert store.is_muted("job3", now=_utc(hour=5)) is False


def test_unmute_removes_entry(store):
    e = MuteEntry(job_name="job4", muted_at=_utc(), muted_until=None)
    store.mute(e)
    store.unmute("job4")
    assert store.get("job4") is None


def test_unmute_nonexistent_is_noop(store):
    store.unmute("ghost")  # should not raise


def test_all_active_filters_expired(store):
    now = _utc(hour=6)
    store.mute(MuteEntry("active", _utc(), muted_until=_utc(hour=12)))
    store.mute(MuteEntry("expired", _utc(), muted_until=_utc(hour=2)))
    store.mute(MuteEntry("indefinite", _utc(), muted_until=None))
    active = store.all_active(now=now)
    assert set(active.keys()) == {"active", "indefinite"}
