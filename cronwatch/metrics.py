"""Lightweight in-process metrics collector for cronwatch."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict

from cronwatch.executor import ExecutionResult


@dataclass
class JobMetrics:
    """Accumulated counters for a single job."""

    total_runs: int = 0
    total_failures: int = 0
    total_duration_seconds: float = 0.0
    last_exit_code: int | None = None

    @property
    def success_rate(self) -> float | None:
        """Return success rate in [0.0, 1.0], or None if no runs yet."""
        if self.total_runs == 0:
            return None
        return (self.total_runs - self.total_failures) / self.total_runs

    @property
    def average_duration(self) -> float | None:
        """Return average run duration in seconds, or None if no runs yet."""
        if self.total_runs == 0:
            return None
        return self.total_duration_seconds / self.total_runs


class MetricsCollector:
    """Thread-safe store of per-job metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: Dict[str, JobMetrics] = {}

    def record(self, result: ExecutionResult) -> None:
        """Update metrics from an ExecutionResult."""
        with self._lock:
            m = self._data.setdefault(result.job_name, JobMetrics())
            m.total_runs += 1
            m.total_duration_seconds += result.duration_seconds
            m.last_exit_code = result.exit_code
            if not result.success:
                m.total_failures += 1

    def get(self, job_name: str) -> JobMetrics | None:
        """Return a *copy* of metrics for *job_name*, or None if unknown."""
        with self._lock:
            m = self._data.get(job_name)
            if m is None:
                return None
            return JobMetrics(
                total_runs=m.total_runs,
                total_failures=m.total_failures,
                total_duration_seconds=m.total_duration_seconds,
                last_exit_code=m.last_exit_code,
            )

    def all(self) -> Dict[str, JobMetrics]:
        """Return a shallow copy of all metrics keyed by job name."""
        with self._lock:
            return {
                name: JobMetrics(
                    total_runs=m.total_runs,
                    total_failures=m.total_failures,
                    total_duration_seconds=m.total_duration_seconds,
                    last_exit_code=m.last_exit_code,
                )
                for name, m in self._data.items()
            }

    def reset(self, job_name: str | None = None) -> None:
        """Reset counters for *job_name*, or all jobs if None."""
        with self._lock:
            if job_name is None:
                self._data.clear()
            else:
                self._data.pop(job_name, None)
