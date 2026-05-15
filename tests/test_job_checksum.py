"""Tests for cronwatch.job_checksum."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwatch.job_checksum import ChecksumEntry, ChecksumStore, _checksum


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def store(tmp_path: Path) -> ChecksumStore:
    return ChecksumStore(str(tmp_path / "checksums.json"))


# ---------------------------------------------------------------------------
# _checksum
# ---------------------------------------------------------------------------

def test_checksum_is_16_chars():
    assert len(_checksum("echo hello")) == 16


def test_checksum_same_command_identical():
    assert _checksum("echo hi") == _checksum("echo hi")


def test_checksum_different_commands_differ():
    assert _checksum("echo hi") != _checksum("echo bye")


# ---------------------------------------------------------------------------
# ChecksumEntry
# ---------------------------------------------------------------------------

def test_entry_from_command_sets_digest():
    entry = ChecksumEntry.from_command("backup", "tar -czf /tmp/x.tgz /data")
    assert entry.digest == _checksum("tar -czf /tmp/x.tgz /data")
    assert entry.job_name == "backup"


# ---------------------------------------------------------------------------
# ChecksumStore — record / get
# ---------------------------------------------------------------------------

def test_record_persists_to_disk(store: ChecksumStore, tmp_path: Path):
    store.record("myjob", "echo 1")
    raw = json.loads((tmp_path / "checksums.json").read_text())
    assert "myjob" in raw


def test_get_returns_none_for_unknown(store: ChecksumStore):
    assert store.get("nonexistent") is None


def test_get_returns_stored_digest(store: ChecksumStore):
    store.record("job-a", "echo a")
    assert store.get("job-a") == _checksum("echo a")


# ---------------------------------------------------------------------------
# ChecksumStore — changed
# ---------------------------------------------------------------------------

def test_changed_false_when_no_prior_record(store: ChecksumStore):
    assert store.changed("new-job", "echo x") is False


def test_changed_false_when_command_same(store: ChecksumStore):
    store.record("job-b", "python run.py")
    assert store.changed("job-b", "python run.py") is False


def test_changed_true_when_command_differs(store: ChecksumStore):
    store.record("job-c", "python run.py")
    assert store.changed("job-c", "python run_v2.py") is True


# ---------------------------------------------------------------------------
# ChecksumStore — persistence across instances
# ---------------------------------------------------------------------------

def test_reload_from_disk(tmp_path: Path):
    path = str(tmp_path / "checksums.json")
    s1 = ChecksumStore(path)
    s1.record("job-d", "bash /opt/run.sh")

    s2 = ChecksumStore(path)
    assert s2.get("job-d") == _checksum("bash /opt/run.sh")


def test_all_entries_returns_copy(store: ChecksumStore):
    store.record("alpha", "cmd1")
    store.record("beta", "cmd2")
    entries = store.all_entries()
    assert set(entries.keys()) == {"alpha", "beta"}
    # mutating the copy must not affect the store
    entries["gamma"] = "x"
    assert store.get("gamma") is None


def test_corrupt_file_treated_as_empty(tmp_path: Path):
    p = tmp_path / "checksums.json"
    p.write_text("not valid json")
    s = ChecksumStore(str(p))
    assert s.all_entries() == {}
