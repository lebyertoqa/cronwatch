"""Periodic digest reporter: aggregates job history and sends summary emails."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from cronwatch.alerting import Alerter
from cronwatch.history import HistoryStore
from cronwatch.reporter import Report, summarise

log = logging.getLogger(__name__)


class DigestSender:
    """Builds a report over a rolling window and dispatches it via an Alerter."""

    def __init__(
        self,
        store: HistoryStore,
        alerter: Alerter,
        window_hours: int = 24,
    ) -> None:
        self._store = store
        self._alerter = alerter
        self._window_hours = window_hours
        self._last_sent: Optional[datetime] = None

    # ------------------------------------------------------------------
    def send_digest(self, now: Optional[datetime] = None) -> bool:
        """Build and send a digest.  Returns True when a digest was sent."""
        now = now or datetime.now(tz=timezone.utc)
        since = now - timedelta(hours=self._window_hours)

        entries = [
            e
            for e in self._store.all()
            if e.finished_at >= since
        ]

        report = Report(entries=entries, generated_at=now)
        subject = self._subject(report, now)
        body = _render(report, since, now)

        log.info("Sending digest: %s", subject)
        self._alerter.send(subject=subject, body=body)
        self._last_sent = now
        return True

    # ------------------------------------------------------------------
    def due(self, interval_hours: int, now: Optional[datetime] = None) -> bool:
        """Return True if enough time has elapsed since the last digest."""
        if self._last_sent is None:
            return True
        now = now or datetime.now(tz=timezone.utc)
        return (now - self._last_sent) >= timedelta(hours=interval_hours)

    # ------------------------------------------------------------------
    @staticmethod
    def _subject(report: Report, now: datetime) -> str:
        stamp = now.strftime("%Y-%m-%d %H:%M UTC")
        failed = report.jobs_with_failures
        if failed:
            names = ", ".join(s.job_name for s in failed)
            return f"[cronwatch] Digest {stamp} — FAILURES: {names}"
        return f"[cronwatch] Digest {stamp} — all jobs healthy"


def _render(report: Report, since: datetime, now: datetime) -> str:
    lines = [
        f"Cronwatch digest — {since.strftime('%Y-%m-%d %H:%M')} to "
        f"{now.strftime('%Y-%m-%d %H:%M')} UTC",
        "",
        f"Total job runs : {report.total_jobs}",
        "",
        "Job summary:",
    ]
    for summary in summarise(report.entries):
        status = "OK" if summary.failure_count == 0 else "FAIL"
        lines.append(
            f"  [{status}] {summary.job_name}: "
            f"{summary.success_count} ok / {summary.failure_count} failed "
            f"(success rate {summary.success_rate:.0%})"
        )
    if not report.entries:
        lines.append("  (no runs recorded in this window)")
    return "\n".join(lines)
