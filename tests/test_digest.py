"""Tests for cronwatch.digest."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, call

import pytest

from cronwatch.digest import DigestSender, _render
from cronwatch.history import HistoryEntry
from cronwatch.reporter import Report


def _utc(offset_hours: float = 0) -> datetime:
    return datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(
        hours=offset_hours
    )


def _entry(job: str, success: bool, offset_hours: float = 0) -> HistoryEntry:
    t = _utc(offset_hours)
    return HistoryEntry(
        job_name=job,
        success=success,
        exit_code=0 if success else 1,
        stdout="",
        stderr="" if success else "boom",
        started_at=t - timedelta(seconds=5),
        finished_at=t,
        duration=5.0,
    )


def _make_store(entries: list[HistoryEntry]) -> MagicMock:
    store = MagicMock()
    store.all.return_value = entries
    return store


def _make_alerter() -> MagicMock:
    alerter = MagicMock()
    return alerter


# ---------------------------------------------------------------------------

class TestDigestSender:
    def test_send_digest_calls_alerter(self):
        store = _make_store([_entry("backup", True, offset_hours=-1)])
        alerter = _make_alerter()
        sender = DigestSender(store, alerter, window_hours=24)
        result = sender.send_digest(now=_utc())
        assert result is True
        alerter.send.assert_called_once()

    def test_subject_contains_failure_name_on_failure(self):
        store = _make_store([_entry("backup", False, offset_hours=-1)])
        alerter = _make_alerter()
        sender = DigestSender(store, alerter, window_hours=24)
        sender.send_digest(now=_utc())
        subject = alerter.send.call_args.kwargs["subject"]
        assert "FAILURES" in subject
        assert "backup" in subject

    def test_subject_healthy_when_all_pass(self):
        store = _make_store([_entry("sync", True, offset_hours=-2)])
        alerter = _make_alerter()
        sender = DigestSender(store, alerter, window_hours=24)
        sender.send_digest(now=_utc())
        subject = alerter.send.call_args.kwargs["subject"]
        assert "healthy" in subject

    def test_entries_outside_window_excluded(self):
        old = _entry("old", False, offset_hours=-30)
        recent = _entry("recent", True, offset_hours=-1)
        store = _make_store([old, recent])
        alerter = _make_alerter()
        sender = DigestSender(store, alerter, window_hours=24)
        sender.send_digest(now=_utc())
        body = alerter.send.call_args.kwargs["body"]
        assert "recent" in body
        assert "old" not in body

    def test_due_returns_true_when_never_sent(self):
        sender = DigestSender(_make_store([]), _make_alerter())
        assert sender.due(interval_hours=6) is True

    def test_due_returns_false_within_interval(self):
        sender = DigestSender(_make_store([]), _make_alerter())
        sender.send_digest(now=_utc())
        assert sender.due(interval_hours=6, now=_utc(offset_hours=3)) is False

    def test_due_returns_true_after_interval(self):
        sender = DigestSender(_make_store([]), _make_alerter())
        sender.send_digest(now=_utc())
        assert sender.due(interval_hours=6, now=_utc(offset_hours=7)) is True

    def test_empty_window_renders_no_runs_message(self):
        store = _make_store([])
        alerter = _make_alerter()
        sender = DigestSender(store, alerter, window_hours=24)
        sender.send_digest(now=_utc())
        body = alerter.send.call_args.kwargs["body"]
        assert "no runs recorded" in body
