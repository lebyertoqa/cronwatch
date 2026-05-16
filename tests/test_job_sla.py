"""Tests for cronwatch.job_sla and cronwatch.sla_alerter."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pytest

from cronwatch.history import HistoryEntry, HistoryStore
from cronwatch.job_sla import SLAPolicy, SLATracker, evaluate_sla
from cronwatch.sla_alerter import SLAAlerter


def _utc(year=2024, month=1, day=1, hour=0, minute=0, second=0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


def _entry(
    job_name: str,
    success: bool,
    duration: float = 1.0,
    started_at: datetime | None = None,
) -> HistoryEntry:
    return HistoryEntry(
        job_name=job_name,
        success=success,
        exit_code=0 if success else 1,
        duration_seconds=duration,
        started_at=started_at or _utc(),
        stdout="",
        stderr="",
    )


@pytest.fixture()
def store(tmp_path: Path) -> HistoryStore:
    return HistoryStore(str(tmp_path / "history"))


# ---------------------------------------------------------------------------
# evaluate_sla
# ---------------------------------------------------------------------------

def test_evaluate_sla_no_entries_is_healthy():
    policy = SLAPolicy(min_success_rate=0.9, window_hours=24)
    status = evaluate_sla("myjob", [], policy)
    assert status.healthy
    assert status.total_runs == 0


def test_evaluate_sla_all_success():
    entries = [_entry("j", True) for _ in range(5)]
    policy = SLAPolicy(min_success_rate=1.0, window_hours=24)
    status = evaluate_sla("j", entries, policy)
    assert status.success_rate == 1.0
    assert status.meets_success_rate
    assert status.healthy


def test_evaluate_sla_below_threshold():
    entries = [_entry("j", True), _entry("j", False), _entry("j", False)]
    policy = SLAPolicy(min_success_rate=0.9, window_hours=24)
    status = evaluate_sla("j", entries, policy)
    assert not status.meets_success_rate
    assert not status.healthy


def test_evaluate_sla_duration_breach():
    entries = [_entry("j", True, duration=120.0)]
    policy = SLAPolicy(min_success_rate=0.0, max_duration_seconds=60.0, window_hours=24)
    status = evaluate_sla("j", entries, policy)
    assert not status.meets_duration
    assert not status.healthy


def test_evaluate_sla_duration_ok_when_zero_limit():
    entries = [_entry("j", True, duration=9999.0)]
    policy = SLAPolicy(max_duration_seconds=0.0, window_hours=24)
    status = evaluate_sla("j", entries, policy)
    assert status.meets_duration


def test_evaluate_sla_per_job_override():
    per_job_policy = SLAPolicy(min_success_rate=0.5, window_hours=24)
    policy = SLAPolicy(
        min_success_rate=1.0,
        window_hours=24,
        per_job={"j": per_job_policy},
    )
    entries = [_entry("j", True), _entry("j", False)]
    status = evaluate_sla("j", entries, policy)
    # 50% meets the per-job threshold of 0.5
    assert status.meets_success_rate


# ---------------------------------------------------------------------------
# SLATracker
# ---------------------------------------------------------------------------

def test_tracker_violations_returns_unhealthy(store: HistoryStore):
    for _ in range(3):
        store.record(_entry("bad_job", False))
    store.record(_entry("good_job", True))

    policy = SLAPolicy(min_success_rate=1.0, window_hours=24)
    tracker = SLATracker(store, policy)
    violations = tracker.violations(["bad_job", "good_job"])
    assert len(violations) == 1
    assert violations[0].job_name == "bad_job"


# ---------------------------------------------------------------------------
# SLAAlerter
# ---------------------------------------------------------------------------

class _FakeAlerter:
    def __init__(self):
        self.calls: List[dict] = []

    def send(self, *, subject: str, body: str) -> None:
        self.calls.append({"subject": subject, "body": body})


def test_sla_alerter_sends_on_first_violation(store: HistoryStore):
    store.record(_entry("j", False))
    policy = SLAPolicy(min_success_rate=1.0, window_hours=24)
    tracker = SLATracker(store, policy)
    alerter = _FakeAlerter()
    sla_alerter = SLAAlerter(tracker, alerter)

    violations = sla_alerter.check(["j"])
    assert len(violations) == 1
    assert len(alerter.calls) == 1
    assert "j" in alerter.calls[0]["subject"]


def test_sla_alerter_deduplicates_repeated_checks(store: HistoryStore):
    store.record(_entry("j", False))
    policy = SLAPolicy(min_success_rate=1.0, window_hours=24)
    tracker = SLATracker(store, policy)
    alerter = _FakeAlerter()
    sla_alerter = SLAAlerter(tracker, alerter)

    sla_alerter.check(["j"])
    sla_alerter.check(["j"])  # still in violation — no second alert
    assert len(alerter.calls) == 1


def test_sla_alerter_re_alerts_after_recovery(store: HistoryStore):
    store.record(_entry("j", True))
    policy = SLAPolicy(min_success_rate=1.0, window_hours=24)
    tracker = SLATracker(store, policy)
    alerter = _FakeAlerter()
    sla_alerter = SLAAlerter(tracker, alerter)

    # Healthy — no alert.
    sla_alerter.check(["j"])
    assert len(alerter.calls) == 0

    # Simulate new failure by adding a bad entry and patching tracker.
    store.record(_entry("j", False))
    sla_alerter._tracker = SLATracker(store, SLAPolicy(min_success_rate=1.0, window_hours=24))
    sla_alerter.check(["j"])
    assert len(alerter.calls) == 1
