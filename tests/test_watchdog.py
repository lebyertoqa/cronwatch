"""Tests for cronwatch.watchdog."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from cronwatch.watchdog import MissedJob, Watchdog, check_missed


def _utc(**kwargs) -> datetime:
    return datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc) + timedelta(**kwargs)


def _job(name: str, interval: int):
    j = MagicMock()
    j.name = name
    j.interval_seconds = interval
    return j


def _entry(started_at: datetime):
    e = MagicMock()
    e.started_at = started_at
    return e


def _store(entries_by_name: dict):
    store = MagicMock()
    store.get.side_effect = lambda name: entries_by_name.get(name, [])
    return store


# ---------------------------------------------------------------------------
# check_missed unit tests
# ---------------------------------------------------------------------------

def test_no_jobs_returns_empty():
    result = check_missed([], _store({}), grace_seconds=0, now=_utc())
    assert result == []


def test_job_without_interval_skipped():
    job = _job("noop", 0)
    result = check_missed([job], _store({}), grace_seconds=0, now=_utc())
    assert result == []


def test_recently_run_job_not_missed():
    job = _job("hourly", 3600)
    store = _store({"hourly": [_entry(_utc(seconds=-100))]})
    result = check_missed([job], store, grace_seconds=60, now=_utc())
    assert result == []


def test_overdue_job_detected():
    job = _job("hourly", 3600)
    # Last run was 2 hours ago — definitely overdue
    store = _store({"hourly": [_entry(_utc(seconds=-7200))]})
    result = check_missed([job], store, grace_seconds=60, now=_utc())
    assert len(result) == 1
    assert result[0].job_name == "hourly"


def test_missed_job_carries_last_run():
    job = _job("daily", 86400)
    last = _utc(seconds=-90000)
    store = _store({"daily": [_entry(last)]})
    result = check_missed([job], store, grace_seconds=60, now=_utc())
    assert result[0].last_run == last


def test_job_never_run_is_missed():
    job = _job("fresh", 300)
    store = _store({})
    # Use a far-future 'now' so the epoch-based deadline is long past
    future = _utc(seconds=999999)
    result = check_missed([job], store, grace_seconds=0, now=future)
    assert any(m.job_name == "fresh" for m in result)


def test_missed_job_str_contains_name():
    m = MissedJob(
        job_name="myjob",
        last_run=None,
        expected_by=_utc(),
        grace_seconds=30,
    )
    assert "myjob" in str(m)
    assert "never" in str(m)


# ---------------------------------------------------------------------------
# Watchdog integration tests
# ---------------------------------------------------------------------------

def test_watchdog_sends_alert_for_missed_job():
    job = _job("hourly", 3600)
    store = _store({"hourly": [_entry(_utc(seconds=-7200))]})
    alerter = MagicMock()
    wd = Watchdog([job], store, alerter, grace_seconds=60)
    missed = wd.check(now=_utc())
    assert len(missed) == 1
    alerter.send.assert_called_once()
    call_kwargs = alerter.send.call_args.kwargs
    assert "hourly" in call_kwargs["subject"]


def test_watchdog_suppresses_duplicate_alert_within_hour():
    job = _job("hourly", 3600)
    store = _store({"hourly": [_entry(_utc(seconds=-7200))]})
    alerter = MagicMock()
    wd = Watchdog([job], store, alerter, grace_seconds=60)
    wd.check(now=_utc())
    wd.check(now=_utc(seconds=30))  # 30 s later — should be suppressed
    assert alerter.send.call_count == 1


def test_watchdog_re_alerts_after_one_hour():
    job = _job("hourly", 3600)
    store = _store({"hourly": [_entry(_utc(seconds=-7200))]})
    alerter = MagicMock()
    wd = Watchdog([job], store, alerter, grace_seconds=60)
    wd.check(now=_utc())
    wd.check(now=_utc(seconds=3601))  # just over an hour later
    assert alerter.send.call_count == 2
