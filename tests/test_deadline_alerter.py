"""Tests for cronwatch.deadline_alerter."""
from __future__ import annotations

import types
from datetime import datetime, timezone
from unittest.mock import MagicMock, call

from cronwatch.deadline_alerter import DeadlineAlerter
from cronwatch.job_deadline import DeadlineChecker


def _utc(h: int, m: int, s: int = 0) -> datetime:
    return datetime(2024, 6, 1, h, m, s, tzinfo=timezone.utc)


def _job(name: str, deadline: str | None = None):
    return types.SimpleNamespace(name=name, deadline=deadline)


def _make(jobs, /):
    checker = DeadlineChecker(jobs=jobs)
    alerter = MagicMock()
    da = DeadlineAlerter(checker=checker, alerter=alerter)
    return da, checker, alerter


def test_no_violations_no_alert_sent():
    da, _, mock_alerter = _make([_job("report", "10:00")])
    da.tick(now=_utc(9, 59))
    mock_alerter.send.assert_not_called()


def test_violation_triggers_alert():
    da, _, mock_alerter = _make([_job("report", "10:00")])
    da.tick(now=_utc(10, 1))
    mock_alerter.send.assert_called_once()


def test_alert_subject_contains_job_name():
    da, _, mock_alerter = _make([_job("nightly", "02:00")])
    da.tick(now=_utc(2, 5))
    subject = mock_alerter.send.call_args[0][0]
    assert "nightly" in subject


def test_alert_body_contains_deadline():
    da, _, mock_alerter = _make([_job("sync", "06:30")])
    da.tick(now=_utc(6, 35))
    body = mock_alerter.send.call_args[0][1]
    assert "06:30 UTC" in body


def test_second_tick_same_day_does_not_resend():
    da, _, mock_alerter = _make([_job("report", "10:00")])
    da.tick(now=_utc(10, 1))
    da.tick(now=_utc(10, 2))
    assert mock_alerter.send.call_count == 1


def test_reset_daily_allows_resend():
    da, _, mock_alerter = _make([_job("report", "10:00")])
    da.tick(now=_utc(10, 1))
    da.reset_daily()
    da.tick(now=_utc(10, 3))
    assert mock_alerter.send.call_count == 2


def test_dispatched_before_deadline_suppresses_alert():
    job = _job("backup", "08:00")
    da, checker, mock_alerter = _make([job])
    checker.mark_dispatched("backup", when=_utc(7, 50))
    da.tick(now=_utc(8, 5))
    mock_alerter.send.assert_not_called()


def test_multiple_violations_each_alerted():
    j1 = _job("alpha", "06:00")
    j2 = _job("beta", "07:00")
    da, _, mock_alerter = _make([j1, j2])
    da.tick(now=_utc(8, 0))
    assert mock_alerter.send.call_count == 2


def test_tick_returns_new_violations_only():
    da, _, _ = _make([_job("report", "10:00")])
    first = da.tick(now=_utc(10, 1))
    second = da.tick(now=_utc(10, 2))
    assert len(first) == 1
    assert len(second) == 0


def test_job_without_deadline_never_alerts():
    da, _, mock_alerter = _make([_job("cleanup")])
    da.tick(now=_utc(23, 59))
    mock_alerter.send.assert_not_called()
