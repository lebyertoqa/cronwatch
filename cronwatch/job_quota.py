"""Per-job execution quota enforcement.

Limits how many times a job may run within a rolling time window.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class QuotaPolicy:
    """Defines quota limits, optionally overridden per job."""

    default_max_runs: int = 0          # 0 means unlimited
    default_window_seconds: int = 3600
    per_job: Dict[str, dict] = field(default_factory=dict)

    def max_runs_for(self, job_name: str) -> int:
        override = self.per_job.get(job_name, {})
        return int(override.get("max_runs", self.default_max_runs))

    def window_seconds_for(self, job_name: str) -> int:
        override = self.per_job.get(job_name, {})
        return int(override.get("window_seconds", self.default_window_seconds))


@dataclass
class _QuotaWindow:
    timestamps: List[datetime] = field(default_factory=list)

    def evict_before(self, cutoff: datetime) -> None:
        self.timestamps = [t for t in self.timestamps if t >= cutoff]

    def count(self) -> int:
        return len(self.timestamps)

    def record(self, ts: datetime) -> None:
        self.timestamps.append(ts)


class QuotaExceededError(Exception):
    """Raised when a job has exhausted its quota for the current window."""

    def __init__(self, job_name: str, max_runs: int, window_seconds: int) -> None:
        self.job_name = job_name
        self.max_runs = max_runs
        self.window_seconds = window_seconds
        super().__init__(
            f"Job '{job_name}' has reached its quota of {max_runs} runs "
            f"within the last {window_seconds}s"
        )


class QuotaTracker:
    """Tracks and enforces per-job run quotas."""

    def __init__(self, policy: QuotaPolicy) -> None:
        self._policy = policy
        self._windows: Dict[str, _QuotaWindow] = {}

    def _window(self, job_name: str) -> _QuotaWindow:
        if job_name not in self._windows:
            self._windows[job_name] = _QuotaWindow()
        return self._windows[job_name]

    def check(self, job_name: str, now: Optional[datetime] = None) -> None:
        """Raise QuotaExceededError if the job has exhausted its quota."""
        max_runs = self._policy.max_runs_for(job_name)
        if max_runs == 0:
            return  # unlimited
        window_secs = self._policy.window_seconds_for(job_name)
        ts = now or _utcnow()
        cutoff = ts - timedelta(seconds=window_secs)
        win = self._window(job_name)
        win.evict_before(cutoff)
        if win.count() >= max_runs:
            raise QuotaExceededError(job_name, max_runs, window_secs)

    def record(self, job_name: str, now: Optional[datetime] = None) -> None:
        """Record that the job ran at the given time."""
        ts = now or _utcnow()
        self._window(job_name).record(ts)

    def remaining(self, job_name: str, now: Optional[datetime] = None) -> Optional[int]:
        """Return remaining runs allowed, or None if unlimited."""
        max_runs = self._policy.max_runs_for(job_name)
        if max_runs == 0:
            return None
        window_secs = self._policy.window_seconds_for(job_name)
        ts = now or _utcnow()
        cutoff = ts - timedelta(seconds=window_secs)
        win = self._window(job_name)
        win.evict_before(cutoff)
        return max(0, max_runs - win.count())
