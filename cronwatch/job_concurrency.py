"""Controls maximum concurrency for cron jobs."""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Semaphore
from typing import Dict, Optional

from cronwatch.config import JobConfig

_DEFAULT_MAX_CONCURRENT = 1


@dataclass
class ConcurrencyPolicy:
    """Maps job names to their maximum concurrency limits."""

    default: int = _DEFAULT_MAX_CONCURRENT
    per_job: Dict[str, int] = field(default_factory=dict)

    def limit_for(self, job: JobConfig) -> int:
        """Return the concurrency limit for *job*."""
        return self.per_job.get(job.name, self.default)


class ConcurrencySlotUnavailable(Exception):
    """Raised when no concurrency slot is available for a job."""

    def __init__(self, job_name: str) -> None:
        super().__init__(f"No concurrency slot available for job '{job_name}'")
        self.job_name = job_name


class ConcurrencyGuard:
    """Manages per-job semaphores to enforce concurrency limits."""

    def __init__(self, policy: ConcurrencyPolicy) -> None:
        self._policy = policy
        self._semaphores: Dict[str, Semaphore] = {}

    def _semaphore_for(self, job: JobConfig) -> Semaphore:
        if job.name not in self._semaphores:
            limit = self._policy.limit_for(job)
            self._semaphores[job.name] = Semaphore(max(1, limit))
        return self._semaphores[job.name]

    def acquire(self, job: JobConfig, block: bool = False) -> bool:
        """Acquire a slot for *job*.  Returns True on success.

        If *block* is False (default) and no slot is free, returns False
        immediately without raising.
        """
        sem = self._semaphore_for(job)
        return sem.acquire(blocking=block)

    def release(self, job: JobConfig) -> None:
        """Release a previously acquired slot for *job*."""
        sem = self._semaphore_for(job)
        sem.release()

    def try_acquire(self, job: JobConfig) -> None:
        """Acquire a slot or raise :exc:`ConcurrencySlotUnavailable`."""
        if not self.acquire(job, block=False):
            raise ConcurrencySlotUnavailable(job.name)


def build_concurrency_guard(
    default: int = _DEFAULT_MAX_CONCURRENT,
    per_job: Optional[Dict[str, int]] = None,
) -> ConcurrencyGuard:
    """Convenience factory used by the application bootstrap."""
    policy = ConcurrencyPolicy(default=default, per_job=per_job or {})
    return ConcurrencyGuard(policy)
