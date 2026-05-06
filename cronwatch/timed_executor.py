"""Executor wrapper that enforces per-job timeouts."""

from __future__ import annotations

from cronwatch.executor import ExecutionResult, run_job
from cronwatch.config import JobConfig
from cronwatch.job_timeout import TimeoutPolicy, JobTimeoutError, enforce_timeout


class TimedExecutor:
    """Runs jobs through the standard executor but kills them if they
    exceed the configured deadline.

    Parameters
    ----------
    policy:
        A :class:`TimeoutPolicy` that maps job names to timeout values.
    """

    def __init__(self, policy: TimeoutPolicy) -> None:
        self._policy = policy

    def run(self, job: JobConfig) -> ExecutionResult:
        """Execute *job*, returning a failed :class:`ExecutionResult` if it
        times out instead of propagating the exception.
        """
        timeout = self._policy.timeout_for(job.name)
        try:
            with enforce_timeout(job.name, timeout):
                return run_job(job)
        except JobTimeoutError as exc:
            return ExecutionResult(
                job_name=job.name,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(exc),
                duration=float(timeout),
            )


def build_timed_executor(
    default_seconds: int = 3600,
    per_job: dict[str, int] | None = None,
) -> TimedExecutor:
    """Convenience factory used by :mod:`cronwatch.__main__`."""
    policy = TimeoutPolicy(default_seconds=default_seconds, per_job=per_job or {})
    return TimedExecutor(policy)
