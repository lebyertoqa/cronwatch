"""Tracks the current execution status of each job (idle, running, failed, succeeded)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional

from cronwatch.executor import ExecutionResult


class JobState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class JobStatus:
    job_name: str
    state: JobState = JobState.IDLE
    last_started_at: Optional[datetime] = None
    last_finished_at: Optional[datetime] = None
    last_result: Optional[ExecutionResult] = None
    consecutive_failures: int = 0

    def mark_running(self) -> None:
        self.state = JobState.RUNNING
        self.last_started_at = _utcnow()

    def mark_finished(self, result: ExecutionResult) -> None:
        self.last_finished_at = _utcnow()
        self.last_result = result
        if result.success:
            self.state = JobState.SUCCEEDED
            self.consecutive_failures = 0
        else:
            self.state = JobState.FAILED
            self.consecutive_failures += 1

    @property
    def is_healthy(self) -> bool:
        return self.state in (JobState.IDLE, JobState.SUCCEEDED)


@dataclass
class JobStatusRegistry:
    _statuses: Dict[str, JobStatus] = field(default_factory=dict)

    def get(self, job_name: str) -> JobStatus:
        if job_name not in self._statuses:
            self._statuses[job_name] = JobStatus(job_name=job_name)
        return self._statuses[job_name]

    def mark_running(self, job_name: str) -> None:
        self.get(job_name).mark_running()

    def mark_finished(self, job_name: str, result: ExecutionResult) -> None:
        self.get(job_name).mark_finished(result)

    def all_statuses(self) -> Dict[str, JobStatus]:
        return dict(self._statuses)

    def unhealthy_jobs(self) -> Dict[str, JobStatus]:
        return {name: s for name, s in self._statuses.items() if not s.is_healthy}

    def reset(self, job_name: str) -> None:
        if job_name in self._statuses:
            del self._statuses[job_name]
