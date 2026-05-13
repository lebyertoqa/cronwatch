"""Executor wrapper that enforces per-job concurrency limits."""
from __future__ import annotations

from cronwatch.config import JobConfig
from cronwatch.executor import ExecutionResult
from cronwatch.job_concurrency import ConcurrencyGuard, ConcurrencySlotUnavailable


class ConcurrentExecutor:
    """Wraps an inner executor and gates execution via a :class:`ConcurrencyGuard`.

    If no slot is available the job is skipped and a synthetic failure result
    is returned so the rest of the pipeline (alerting, history) can handle it
    uniformly.
    """

    def __init__(self, inner, guard: ConcurrencyGuard) -> None:
        self._inner = inner
        self._guard = guard

    def run(self, job: JobConfig) -> ExecutionResult:
        """Run *job* if a concurrency slot is available."""
        try:
            self._guard.try_acquire(job)
        except ConcurrencySlotUnavailable:
            return ExecutionResult(
                job_name=job.name,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Skipped: concurrency limit reached for '{job.name}'",
                duration=0.0,
            )

        try:
            return self._inner.run(job)
        finally:
            self._guard.release(job)


def build_concurrent_executor(inner, guard: ConcurrencyGuard) -> ConcurrentExecutor:
    """Convenience factory."""
    return ConcurrentExecutor(inner=inner, guard=guard)
