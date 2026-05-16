"""Tests for cronwatch.job_changelog."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pytest

from cronwatch.job_changelog import (
    ChangelogEntry,
    ChangelogStore,
    JobSnapshot,
    diff_snapshots,
)


def _utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


@pytest.fixture()
def store(tmp_path):
    return ChangelogStore(str(tmp_path / "changelog" / "changes.json"))


def test_record_creates_file(store, tmp_path):
    entry = ChangelogEntry(
        job_name="backup",
        changed_at=_utc(2024, 1, 1),
        field_name="schedule",
        old_value="0 1 * * *",
        new_value="0 2 * * *",
    )
    store.record(entry)
    assert os.path.exists(store._path)


def test_record_and_retrieve(store):
    entry = ChangelogEntry(
        job_name="backup",
        changed_at=_utc(2024, 1, 1),
        field_name="schedule",
        old_value="0 1 * * *",
        new_value="0 2 * * *",
    )
    store.record(entry)
    entries = store.entries_for("backup")
    assert len(entries) == 1
    assert entries[0].field_name == "schedule"
    assert entries[0].old_value == "0 1 * * *"
    assert entries[0].new_value == "0 2 * * *"


def test_entries_for_filters_by_job(store):
    for name in ("alpha", "beta", "alpha"):
        store.record(
            ChangelogEntry(
                job_name=name,
                changed_at=_utc(2024, 1, 1),
                field_name="command",
                old_value="old",
                new_value="new",
            )
        )
    assert len(store.entries_for("alpha")) == 2
    assert len(store.entries_for("beta")) == 1


def test_all_entries_returns_everything(store):
    for i in range(3):
        store.record(
            ChangelogEntry(
                job_name=f"job{i}",
                changed_at=_utc(2024, 1, i + 1),
                field_name="schedule",
                old_value=None,
                new_value="* * * * *",
            )
        )
    assert len(store.all_entries()) == 3


def test_empty_store_returns_empty_list(store):
    assert store.all_entries() == []
    assert store.entries_for("anything") == []


def test_diff_snapshots_records_changed_field(store):
    before = JobSnapshot("myjob", _utc(2024, 1, 1), {"schedule": "0 1 * * *"})
    after = JobSnapshot("myjob", _utc(2024, 1, 2), {"schedule": "0 2 * * *"})
    changes = diff_snapshots(before, after, store, now=_utc(2024, 1, 2))
    assert len(changes) == 1
    assert changes[0].field_name == "schedule"


def test_diff_snapshots_no_change_records_nothing(store):
    before = JobSnapshot("myjob", _utc(2024, 1, 1), {"schedule": "0 1 * * *"})
    after = JobSnapshot("myjob", _utc(2024, 1, 2), {"schedule": "0 1 * * *"})
    changes = diff_snapshots(before, after, store, now=_utc(2024, 1, 2))
    assert changes == []
    assert store.entries_for("myjob") == []


def test_diff_snapshots_detects_added_field(store):
    before = JobSnapshot("myjob", _utc(2024, 1, 1), {})
    after = JobSnapshot("myjob", _utc(2024, 1, 2), {"timeout": 30})
    changes = diff_snapshots(before, after, store, now=_utc(2024, 1, 2))
    assert len(changes) == 1
    assert changes[0].old_value is None
    assert changes[0].new_value == 30


def test_diff_snapshots_detects_removed_field(store):
    before = JobSnapshot("myjob", _utc(2024, 1, 1), {"timeout": 30})
    after = JobSnapshot("myjob", _utc(2024, 1, 2), {})
    changes = diff_snapshots(before, after, store, now=_utc(2024, 1, 2))
    assert len(changes) == 1
    assert changes[0].old_value == 30
    assert changes[0].new_value is None


def test_entry_round_trips_via_dict():
    entry = ChangelogEntry(
        job_name="x",
        changed_at=_utc(2024, 6, 15, 12),
        field_name="command",
        old_value="echo old",
        new_value="echo new",
    )
    restored = ChangelogEntry.from_dict(entry.to_dict())
    assert restored.job_name == entry.job_name
    assert restored.changed_at == entry.changed_at
    assert restored.field_name == entry.field_name
    assert restored.old_value == entry.old_value
    assert restored.new_value == entry.new_value
