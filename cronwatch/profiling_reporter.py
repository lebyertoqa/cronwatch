"""Generates a human-readable profiling report across all tracked jobs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from cronwatch.job_profiling import DurationStats, ProfilingStore


@dataclass
class ProfilingReportRow:
    job_name: str
    count: int
    mean: Optional[float]
    minimum: Optional[float]
    maximum: Optional[float]
    p95: Optional[float]

    def is_slow(self, threshold_seconds: float) -> bool:
        """Return True if p95 exceeds the given threshold."""
        return self.p95 is not None and self.p95 > threshold_seconds


@dataclass
class ProfilingReport:
    rows: List[ProfilingReportRow]

    @property
    def total_jobs(self) -> int:
        return len(self.rows)

    def slow_jobs(self, threshold_seconds: float) -> List[ProfilingReportRow]:
        return [r for r in self.rows if r.is_slow(threshold_seconds)]

    def job_names(self) -> List[str]:
        return [r.job_name for r in self.rows]


class ProfilingReporter:
    def __init__(self, store: ProfilingStore) -> None:
        self._store = store

    def _row_from_stats(self, stats: DurationStats) -> ProfilingReportRow:
        return ProfilingReportRow(
            job_name=stats.job_name,
            count=stats.count,
            mean=stats.mean,
            minimum=stats.minimum,
            maximum=stats.maximum,
            p95=stats.p95,
        )

    def build_report(self) -> ProfilingReport:
        rows = [
            self._row_from_stats(self._store.stats_for(name))
            for name in sorted(self._store.all_job_names())
        ]
        return ProfilingReport(rows=rows)

    def report_for_job(self, job_name: str) -> ProfilingReportRow:
        return self._row_from_stats(self._store.stats_for(job_name))
