"""Generates summary reports of cron job execution history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from cronwatch.history import HistoryEntry, HistoryStore


@dataclass
class JobSummary:
    job_name: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    last_run: Optional[datetime]
    last_status: Optional[str]
    avg_duration_seconds: float

    @property
    def success_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return self.successful_runs / self.total_runs * 100.0


@dataclass
class Report:
    generated_at: datetime
    summaries: List[JobSummary]

    @property
    def total_jobs(self) -> int:
        return len(self.summaries)

    @property
    def jobs_with_failures(self) -> List[JobSummary]:
        return [s for s in self.summaries if s.failed_runs > 0]


def _summarise(job_name: str, entries: List[HistoryEntry]) -> JobSummary:
    if not entries:
        return JobSummary(
            job_name=job_name,
            total_runs=0,
            successful_runs=0,
            failed_runs=0,
            last_run=None,
            last_status=None,
            avg_duration_seconds=0.0,
        )

    sorted_entries = sorted(entries, key=lambda e: e.started_at)
    successful = [e for e in sorted_entries if e.exit_code == 0]
    failed = [e for e in sorted_entries if e.exit_code != 0]
    last = sorted_entries[-1]
    durations = [e.duration_seconds for e in sorted_entries if e.duration_seconds is not None]
    avg_duration = sum(durations) / len(durations) if durations else 0.0

    return JobSummary(
        job_name=job_name,
        total_runs=len(sorted_entries),
        successful_runs=len(successful),
        failed_runs=len(failed),
        last_run=last.started_at,
        last_status="success" if last.exit_code == 0 else "failure",
        avg_duration_seconds=round(avg_duration, 3),
    )


def generate_report(store: HistoryStore, job_names: Optional[List[str]] = None) -> Report:
    """Build a Report for the given job names (or all jobs in the store)."""
    names = job_names if job_names is not None else store.list_jobs()
    summaries = [_summarise(name, store.get(name)) for name in sorted(names)]
    return Report(generated_at=datetime.now(timezone.utc), summaries=summaries)
