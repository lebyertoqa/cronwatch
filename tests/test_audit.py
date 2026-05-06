"""Tests for cronwatch.audit."""
import threading
from pathlib import Path

import pytest

from cronwatch.audit import AuditEvent, AuditLog


@pytest.fixture()
def log(tmp_path: Path) -> AuditLog:
    return AuditLog(tmp_path / "audit.jsonl")


# ---------------------------------------------------------------------------
# AuditEvent.now
# ---------------------------------------------------------------------------

def test_event_now_sets_timestamp():
    ev = AuditEvent.now("job_started", "backup")
    assert ev.timestamp  # non-empty ISO string
    assert "T" in ev.timestamp


def test_event_now_no_detail_is_none():
    ev = AuditEvent.now("job_started", "backup")
    assert ev.detail is None


def test_event_now_with_detail():
    ev = AuditEvent.now("alert_sent", "backup", detail="email sent to ops@example.com")
    assert ev.detail == "email sent to ops@example.com"


# ---------------------------------------------------------------------------
# AuditLog.record / read_all
# ---------------------------------------------------------------------------

def test_record_creates_file(log: AuditLog, tmp_path: Path):
    log.record(AuditEvent.now("job_started", "backup"))
    assert (tmp_path / "audit.jsonl").exists()


def test_read_all_empty_before_any_records(log: AuditLog):
    assert log.read_all() == []


def test_record_and_read_round_trip(log: AuditLog):
    ev = AuditEvent.now("job_finished", "cleanup", detail="exit_code=0")
    log.record(ev)
    events = log.read_all()
    assert len(events) == 1
    assert events[0].event == "job_finished"
    assert events[0].job_name == "cleanup"
    assert events[0].detail == "exit_code=0"


def test_multiple_records_preserve_order(log: AuditLog):
    for name in ("a", "b", "c"):
        log.record(AuditEvent.now("job_started", name))
    names = [e.job_name for e in log.read_all()]
    assert names == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# AuditLog.read_for_job
# ---------------------------------------------------------------------------

def test_read_for_job_filters_correctly(log: AuditLog):
    log.record(AuditEvent.now("job_started", "backup"))
    log.record(AuditEvent.now("job_started", "cleanup"))
    log.record(AuditEvent.now("job_finished", "backup"))
    backup_events = log.read_for_job("backup")
    assert len(backup_events) == 2
    assert all(e.job_name == "backup" for e in backup_events)


def test_read_for_job_unknown_returns_empty(log: AuditLog):
    log.record(AuditEvent.now("job_started", "backup"))
    assert log.read_for_job("nonexistent") == []


# ---------------------------------------------------------------------------
# Thread-safety smoke test
# ---------------------------------------------------------------------------

def test_concurrent_writes_do_not_corrupt(log: AuditLog):
    errors: list = []

    def _write(n: int):
        try:
            for _ in range(20):
                log.record(AuditEvent.now("job_started", f"job_{n}"))
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=_write, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert len(log.read_all()) == 100
