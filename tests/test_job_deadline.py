"""Tests for cronwatch.job_deadline."""
from __future__ import annotations

import types
from datetime import datetime, time, timezone

import pytest

from cronwatch.job_deadline import (
    DeadlineChecker,
    DeadlineViolation,
    deadline_for,
    parse_deadline,
)


def _utc(h: int, m: int, s: int = 0) -> datetime:
    return datetime(2024, 6, 1, h, m, s, tzinfo=timezone.utc)


def _job(name: str, deadline: str | None = None):
    obj = types.SimpleNamespace(name=name, deadline=deadline)
    return obj


# ---------------------------------------------------------------------------
# parse_deadline
# ---------------------------------------------------------------------------

def test_parse_deadline_valid():
    t = parse_deadline("08:30")
    assert t.hour == 8 and t.minute == 30


def test_parse_deadline_single_digit_hour():
    t = parse_deadline("9:05")
    assert t.hour == 9 and t.minute == 5


def test_parse_deadline_invalid_format():
    with pytest.raises(ValueError, match="Invalid deadline"):
        parse_deadline("8-30")


def test_parse_deadline_out_of_range():
    with pytest.raises(ValueError, match="out of range"):
        parse_deadline("25:00")


# ---------------------------------------------------------------------------
# deadline_for
# ---------------------------------------------------------------------------

def test_deadline_for_returns_none_when_not_set():
    job = _job("backup")
    assert deadline_for(job) is None


def test_deadline_for_returns_time_when_set():
    job = _job("backup", deadline="06:00")
    t = deadline_for(job)
    assert isinstance(t, time)
    assert t.hour == 6 and t.minute == 0


def test_deadline_for_no_deadline_attribute():
    job = types.SimpleNamespace(name="x")  # no deadline attr
    assert deadline_for(job) is None


# ---------------------------------------------------------------------------
# DeadlineChecker
# ---------------------------------------------------------------------------

def test_no_violations_before_deadline():
    job = _job("report", deadline="10:00")
    checker = DeadlineChecker(jobs=[job])
    violations = checker.check(now=_utc(9, 59))
    assert violations == []


def test_violation_when_deadline_passed_and_not_dispatched():
    job = _job("report", deadline="10:00")
    checker = DeadlineChecker(jobs=[job])
    violations = checker.check(now=_utc(10, 1))
    assert len(violations) == 1
    assert violations[0].job_name == "report"


def test_no_violation_when_dispatched_before_deadline():
    job = _job("report", deadline="10:00")
    checker = DeadlineChecker(jobs=[job])
    checker.mark_dispatched("report", when=_utc(9, 55))
    violations = checker.check(now=_utc(10, 5))
    assert violations == []


def test_violation_when_dispatched_after_deadline():
    job = _job("report", deadline="10:00")
    checker = DeadlineChecker(jobs=[job])
    checker.mark_dispatched("report", when=_utc(10, 3))
    violations = checker.check(now=_utc(10, 5))
    assert len(violations) == 1


def test_jobs_without_deadline_ignored():
    job = _job("cleanup")  # no deadline
    checker = DeadlineChecker(jobs=[job])
    violations = checker.check(now=_utc(23, 59))
    assert violations == []


def test_multiple_jobs_only_overdue_reported():
    j1 = _job("alpha", deadline="08:00")
    j2 = _job("beta", deadline="12:00")
    checker = DeadlineChecker(jobs=[j1, j2])
    checker.mark_dispatched("alpha", when=_utc(7, 50))
    violations = checker.check(now=_utc(12, 1))
    assert len(violations) == 1
    assert violations[0].job_name == "beta"


def test_violation_contains_correct_deadline_time():
    job = _job("sync", deadline="14:30")
    checker = DeadlineChecker(jobs=[job])
    violations = checker.check(now=_utc(14, 31))
    assert violations[0].deadline.hour == 14
    assert violations[0].deadline.minute == 30


def test_violation_contains_checked_at_timestamp():
    job = _job("sync", deadline="14:30")
    checker = DeadlineChecker(jobs=[job])
    now = _utc(14, 35)
    violations = checker.check(now=now)
    assert violations[0].checked_at == now
