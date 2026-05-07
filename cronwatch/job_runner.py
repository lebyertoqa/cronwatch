"""High-level job runner that combines locking, timeout, and execution."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from cronwatch.config import JobConfig
from cronwatch.executor import ExecutionResult, run_job
from cronwatch.job_lock import JobLock, LockAcquisitionError
from cronwatch.job_timeout import TimeoutPolicy, enforce_timeout
from cronwatch.audit_middleware import AuditingExecutor

logger = logging.getLogger(__name__)


@dataclass
class RunnerResult:
    result: Optional[ExecutionResult]
    skipped: bool = False
    skip_reason: str = ""
    lock_path: str = field(default="", repr=False)


class JobRunner:
    """Runs a single job with lock acquisition and timeout enforcement."""

    def __init__(
        self,
        lock_dir: str = "/tmp/cronwatch/locks",
        timeout_policy: Optional[TimeoutPolicy] = None,
        auditing_executor: Optional[AuditingExecutor] = None,
    ) -> None:
        self._lock_dir = lock_dir
        self._timeout_policy = timeout_policy or TimeoutPolicy()
        self._auditing_executor = auditing_executor

    def run(self, job: JobConfig) -> RunnerResult:
        lock = JobLock(job.name, lock_dir=self._lock_dir)
        try:
            lock.acquire()
        except LockAcquisitionError as exc:
            logger.warning("Skipping job %r: %s", job.name, exc)
            return RunnerResult(result=None, skipped=True, skip_reason=str(exc))

        try:
            timeout = self._timeout_policy.timeout_for(job.name)
            result = self._execute(job, timeout)
        finally:
            lock.release()

        return RunnerResult(result=result, lock_path=lock._lock_path)

    def _execute(self, job: JobConfig, timeout: int) -> ExecutionResult:
        if self._auditing_executor is not None:
            raw = self._auditing_executor.run(job)
        else:
            raw = run_job(job)

        if timeout > 0 and raw.duration > timeout:
            logger.warning(
                "Job %r exceeded timeout (%ds), marking as failed.", job.name, timeout
            )
            return ExecutionResult(
                job_name=raw.job_name,
                success=False,
                exit_code=raw.exit_code,
                stdout=raw.stdout,
                stderr=raw.stderr + f"\n[cronwatch] timed out after {timeout}s",
                duration=raw.duration,
                started_at=raw.started_at,
            )
        return raw


def build_job_runner(
    lock_dir: str = "/tmp/cronwatch/locks",
    timeout_policy: Optional[TimeoutPolicy] = None,
    auditing_executor: Optional[AuditingExecutor] = None,
) -> JobRunner:
    return JobRunner(
        lock_dir=lock_dir,
        timeout_policy=timeout_policy,
        auditing_executor=auditing_executor,
    )
