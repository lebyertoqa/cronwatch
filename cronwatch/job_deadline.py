"""Deadline enforcement for cron jobs.

A deadline is a wall-clock time (HH:MM UTC) by which a job must have
started.  If the job has not been dispatched before that time it is
considered overdue and should be skipped or alerted on.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from typing import Dict, List, Optional

from cronwatch.config import JobConfig

_HM_RE = re.compile(r"^(?P<h>\d{1,2}):(?P<m>\d{2})$")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_deadline(value: str) -> time:
    """Parse a 'HH:MM' string into a :class:`datetime.time` (UTC)."""
    m = _HM_RE.match(value.strip())
    if not m:
        raise ValueError(f"Invalid deadline format {value!r}; expected HH:MM")
    h, mn = int(m.group("h")), int(m.group("m"))
    if not (0 <= h <= 23 and 0 <= mn <= 59):
        raise ValueError(f"Deadline {value!r} is out of range")
    return time(h, mn, tzinfo=timezone.utc)


def deadline_for(job: JobConfig) -> Optional[time]:
    """Return the deadline :class:`~datetime.time` for *job*, or ``None``."""
    raw = getattr(job, "deadline", None)
    if raw is None:
        return None
    return parse_deadline(str(raw))


@dataclass
class DeadlineViolation:
    job_name: str
    deadline: time
    checked_at: datetime

    def __str__(self) -> str:  # pragma: no cover
        dl = self.deadline.strftime("%H:%M UTC")
        ts = self.checked_at.strftime("%H:%M:%S UTC")
        return f"{self.job_name}: deadline {dl} exceeded (checked at {ts})"


@dataclass
class DeadlineChecker:
    """Tracks which jobs have been dispatched and reports deadline violations."""

    jobs: List[JobConfig]
    _dispatched: Dict[str, datetime] = field(default_factory=dict, init=False)

    def mark_dispatched(self, job_name: str, when: Optional[datetime] = None) -> None:
        """Record that *job_name* was dispatched at *when* (defaults to now)."""
        self._dispatched[job_name] = when or _utcnow()

    def check(self, now: Optional[datetime] = None) -> List[DeadlineViolation]:
        """Return violations for jobs whose deadline has passed without dispatch."""
        now = now or _utcnow()
        today_date = now.date()
        violations: List[DeadlineViolation] = []
        for job in self.jobs:
            dl = deadline_for(job)
            if dl is None:
                continue
            deadline_dt = datetime(
                today_date.year, today_date.month, today_date.day,
                dl.hour, dl.minute, tzinfo=timezone.utc,
            )
            if now < deadline_dt:
                continue
            dispatched_at = self._dispatched.get(job.name)
            if dispatched_at is None or dispatched_at > deadline_dt:
                violations.append(
                    DeadlineViolation(
                        job_name=job.name,
                        deadline=dl,
                        checked_at=now,
                    )
                )
        return violations
