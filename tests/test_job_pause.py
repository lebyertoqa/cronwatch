"""Tests for cronwatch.job_pause."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cronwatch.job_pause import PauseEntry, PauseStore


def _utc(year=2024, month=1, day=1, hour=0, minute=0, second=0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


@pytest.fixture
def store(tmp_path: Path) -> PauseStore:
    return PauseStore(tmp_path / "pause_state.json")


# --- PauseEntry ---

def test_pause_entry_indefinite_when_no_resume_at():
    e = PauseEntry(job_name="job", paused_at=_utc())
    assert e.is_indefinite() is True


def test_pause_entry_not_indefinite_when_resume_at_set():
    e = PauseEntry(job_name="job", paused_at=_utc(), resume_at=_utc(hour=1))
    assert e.is_indefinite() is False


def test_pause_entry_not_expired_when_indefinite():
    e = PauseEntry(job_name="job", paused_at=_utc())
    assert e.is_expired(_utc(year=2099)) is False


def test_pause_entry_expired_when_past_resume_at():
    e = PauseEntry(job_name="job", paused_at=_utc(), resume_at=_utc(hour=1))
    assert e.is_expired(_utc(hour=2)) is True


def test_pause_entry_not_expired_before_resume_at():
    e = PauseEntry(job_name="job", paused_at=_utc(), resume_at=_utc(hour=2))
    assert e.is_expired(_utc(hour=1)) is False


# --- PauseStore ---

def test_pause_marks_job_as_paused(store: PauseStore):
    store.pause("backup")
    assert store.is_paused("backup") is True


def test_unknown_job_not_paused(store: PauseStore):
    assert store.is_paused("nonexistent") is False


def test_resume_removes_pause(store: PauseStore):
    store.pause("backup")
    store.resume("backup")
    assert store.is_paused("backup") is False


def test_resume_returns_false_when_not_paused(store: PauseStore):
    assert store.resume("ghost") is False


def test_pause_stores_reason(store: PauseStore):
    store.pause("deploy", reason="maintenance window")
    entry = store.get("deploy")
    assert entry is not None
    assert entry.reason == "maintenance window"


def test_expired_pause_auto_removed(store: PauseStore):
    past = _utc(hour=0)
    store.pause("cleanup", resume_at=past)
    now = _utc(hour=1)
    assert store.is_paused("cleanup", now=now) is False
    assert store.get("cleanup") is None


def test_all_paused_returns_all_entries(store: PauseStore):
    store.pause("job_a")
    store.pause("job_b")
    names = {e.job_name for e in store.all_paused()}
    assert names == {"job_a", "job_b"}


def test_state_persists_across_instances(tmp_path: Path):
    path = tmp_path / "pause_state.json"
    s1 = PauseStore(path)
    s1.pause("reports", reason="debugging")

    s2 = PauseStore(path)
    assert s2.is_paused("reports") is True
    entry = s2.get("reports")
    assert entry.reason == "debugging"


def test_resume_persists_across_instances(tmp_path: Path):
    path = tmp_path / "pause_state.json"
    s1 = PauseStore(path)
    s1.pause("reports")
    s1.resume("reports")

    s2 = PauseStore(path)
    assert s2.is_paused("reports") is False


def test_pause_creates_parent_dirs(tmp_path: Path):
    path = tmp_path / "nested" / "dir" / "pause.json"
    s = PauseStore(path)
    s.pause("job")
    assert path.exists()
