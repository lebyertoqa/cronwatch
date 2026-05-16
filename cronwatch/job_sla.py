"""SLA (Service Level Agreement) tracking for cron jobs.

Tracks whether jobs meet their expected success-rate and duration thresholds
over a rolling window, and exposes per-job SLA status.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from cronwatch.history import HistoryEntry, HistoryStore


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SLAPolicy:
    """Global and per-job SLA thresholds."""
    min_success_rate: float = 1.0          # 0.0–1.0
    max_duration_seconds: float = 0.0      # 0 means no limit
    window_hours: int = 24
    per_job: Dict[str, "SLAPolicy"] = field(default_factory=dict)

    def for_job(self, job_name: str) -> "SLAPolicy":
        return self.per_job.get(job_name, self)


@dataclass
class SLAStatus:
    job_name: str
    window_hours: int
    total_runs: int
    successful_runs: int
    success_rate: float
    avg_duration_seconds: float
    meets_success_rate: bool
    meets_duration: bool

    @property
    def healthy(self) -> bool:
        return self.meets_success_rate and self.meets_duration


def evaluate_sla(
    job_name: str,
    entries: List[HistoryEntry],
    policy: SLAPolicy,
) -> SLAStatus:
    """Evaluate SLA compliance for *job_name* using the supplied history entries."""
    p = policy.for_job(job_name)
    cutoff = _utcnow() - timedelta(hours=p.window_hours)
    recent = [e for e in entries if e.started_at >= cutoff]

    total = len(recent)
    if total == 0:
        return SLAStatus(
            job_name=job_name,
            window_hours=p.window_hours,
            total_runs=0,
            successful_runs=0,
            success_rate=1.0,
            avg_duration_seconds=0.0,
            meets_success_rate=True,
            meets_duration=True,
        )

    successes = sum(1 for e in recent if e.success)
    rate = successes / total
    avg_dur = sum(e.duration_seconds for e in recent) / total

    meets_rate = rate >= p.min_success_rate
    meets_dur = (p.max_duration_seconds == 0) or (avg_dur <= p.max_duration_seconds)

    return SLAStatus(
        job_name=job_name,
        window_hours=p.window_hours,
        total_runs=total,
        successful_runs=successes,
        success_rate=rate,
        avg_duration_seconds=avg_dur,
        meets_success_rate=meets_rate,
        meets_duration=meets_dur,
    )


class SLATracker:
    """Evaluate SLA status for all jobs using a HistoryStore."""

    def __init__(self, store: HistoryStore, policy: SLAPolicy) -> None:
        self._store = store
        self._policy = policy

    def status_for(self, job_name: str) -> SLAStatus:
        entries = self._store.entries_for(job_name)
        return evaluate_sla(job_name, entries, self._policy)

    def all_statuses(self, job_names: List[str]) -> List[SLAStatus]:
        return [self.status_for(n) for n in job_names]

    def violations(self, job_names: List[str]) -> List[SLAStatus]:
        return [s for s in self.all_statuses(job_names) if not s.healthy]
