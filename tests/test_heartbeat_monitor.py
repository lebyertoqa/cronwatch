"""Tests for cronwatch.heartbeat_monitor."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, call

from cronwatch.alerting import Alerter
from cronwatch.job_heartbeat import HeartbeatStore
from cronwatch.heartbeat_monitor import HeartbeatMonitor, HeartbeatViolation


def _utc(hour: int = 12, minute: int = 0) -> datetime:
    return datetime(2024, 1, 1, hour, minute, 0, tzinfo=timezone.utc)


@pytest.fixture
def store(tmp_path: Path) -> HeartbeatStore:
    return HeartbeatStore(str(tmp_path / "hb"))


@pytest.fixture
def alerter() -> MagicMock:
    m = MagicMock(spec=Alerter)
    return m


def test_no_entries_no_violations(store, alerter) -> None:
    monitor = HeartbeatMonitor(store, alerter, ttl_seconds=3600)
    violations = monitor.tick(now=_utc())
    assert violations == []
    alerter.send.assert_not_called()


def test_alive_job_no_violation(store, alerter) -> None:
    store.record("backup", _utc(hour=11, minute=50))
    monitor = HeartbeatMonitor(store, alerter, ttl_seconds=3600)
    violations = monitor.tick(now=_utc(hour=12))
    assert violations == []
    alerter.send.assert_not_called()


def test_stale_job_triggers_violation(store, alerter) -> None:
    store.record("backup", _utc(hour=8))
    monitor = HeartbeatMonitor(store, alerter, ttl_seconds=3600)
    violations = monitor.tick(now=_utc(hour=12))
    assert len(violations) == 1
    assert violations[0].job_name == "backup"


def test_stale_job_sends_alert(store, alerter) -> None:
    store.record("backup", _utc(hour=8))
    monitor = HeartbeatMonitor(store, alerter, ttl_seconds=3600)
    monitor.tick(now=_utc(hour=12))
    alerter.send.assert_called_once()
    _, kwargs = alerter.send.call_args
    assert "backup" in kwargs.get("subject", "") or "backup" in str(alerter.send.call_args)


def test_second_tick_within_ttl_suppressed(store, alerter) -> None:
    store.record("backup", _utc(hour=8))
    monitor = HeartbeatMonitor(store, alerter, ttl_seconds=3600)
    monitor.tick(now=_utc(hour=12))
    monitor.tick(now=_utc(hour=12, minute=10))
    assert alerter.send.call_count == 1


def test_second_tick_after_ttl_re_alerts(store, alerter) -> None:
    store.record("backup", _utc(hour=8))
    monitor = HeartbeatMonitor(store, alerter, ttl_seconds=3600)
    monitor.tick(now=_utc(hour=12))
    # advance by more than one TTL
    monitor.tick(now=_utc(hour=14))
    assert alerter.send.call_count == 2


def test_per_job_ttl_overrides_default(store, alerter) -> None:
    store.record("fast_job", _utc(hour=11, minute=50))
    monitor = HeartbeatMonitor(
        store, alerter, ttl_seconds=3600, per_job_ttl={"fast_job": 60}
    )
    violations = monitor.tick(now=_utc(hour=12))
    assert len(violations) == 1


def test_reset_clears_alerted_state(store, alerter) -> None:
    store.record("backup", _utc(hour=8))
    monitor = HeartbeatMonitor(store, alerter, ttl_seconds=3600)
    monitor.tick(now=_utc(hour=12))
    monitor.reset("backup")
    monitor.tick(now=_utc(hour=12, minute=5))
    assert alerter.send.call_count == 2


def test_violation_str_contains_job_name() -> None:
    v = HeartbeatViolation(
        job_name="nightly",
        last_success=_utc(hour=8),
        age_seconds=14400,
        ttl_seconds=3600,
    )
    assert "nightly" in str(v)
    assert "14400" in str(v)
