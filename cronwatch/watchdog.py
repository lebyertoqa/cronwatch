"""Watchdog: detects jobs that have not run within their expected window."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from cronwatch.config import JobConfig
from cronwatch.history import HistoryStore


@dataclass
class MissedJob:
    job_name: str
    last_run: Optional[datetime]
    expected_by: datetime
    grace_seconds: int

    def __str__(self) -> str:
        last = self.last_run.isoformat() if self.last_run else "never"
        return (
            f"Job '{self.job_name}' missed its window "
            f"(expected by {self.expected_by.isoformat()}, last run: {last})"
        )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def check_missed(
    jobs: List[JobConfig],
    store: HistoryStore,
    grace_seconds: int = 60,
    now: Optional[datetime] = None,
) -> List[MissedJob]:
    """Return a list of jobs whose last recorded run is overdue.

    A job is considered missed when *now* is more than
    ``schedule_interval_seconds + grace_seconds`` past the most recent
    expected run time derived from the last recorded execution.
    """
    if now is None:
        now = _utcnow()

    missed: List[MissedJob] = []

    for job in jobs:
        interval = getattr(job, "interval_seconds", None)
        if interval is None or interval <= 0:
            continue

        entries = store.get(job.name)
        last_run: Optional[datetime] = None
        if entries:
            last_run = max(e.started_at for e in entries)

        if last_run is None:
            # Job has never run — treat epoch as baseline so very old jobs fire
            baseline = datetime(1970, 1, 1, tzinfo=timezone.utc)
        else:
            baseline = last_run

        expected_by = baseline.replace(
            second=baseline.second, microsecond=0
        ) + __import__("datetime").timedelta(seconds=interval)

        deadline = expected_by + __import__("datetime").timedelta(seconds=grace_seconds)

        if now > deadline:
            missed.append(
                MissedJob(
                    job_name=job.name,
                    last_run=last_run,
                    expected_by=expected_by,
                    grace_seconds=grace_seconds,
                )
            )

    return missed


class Watchdog:
    """Periodic watchdog that emits missed-job alerts via an Alerter."""

    def __init__(
        self,
        jobs: List[JobConfig],
        store: HistoryStore,
        alerter,
        grace_seconds: int = 60,
    ) -> None:
        self._jobs = jobs
        self._store = store
        self._alerter = alerter
        self._grace = grace_seconds
        self._alerted: Dict[str, datetime] = {}

    def check(self, now: Optional[datetime] = None) -> List[MissedJob]:
        """Check for missed jobs and send alerts; returns the missed list."""
        if now is None:
            now = _utcnow()

        missed = check_missed(self._jobs, self._store, self._grace, now=now)
        for m in missed:
            last_alerted = self._alerted.get(m.job_name)
            if last_alerted is None or (now - last_alerted).total_seconds() >= 3600:
                self._alerter.send(subject=f"[cronwatch] Missed job: {m.job_name}",
                                   body=str(m))
                self._alerted[m.job_name] = now
        return missed
