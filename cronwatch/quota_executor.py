"""Executor wrapper that enforces job quotas before running."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol

from cronwatch.executor import ExecutionResult
from cronwatch.job_quota import QuotaExceededError, QuotaPolicy, QuotaTracker


class _InnerExecutor(Protocol):
    def run(self, job) -> ExecutionResult: ...


@dataclass
class QuotaResult:
    """Wraps an ExecutionResult, adding quota metadata."""

    result: Optional[ExecutionResult]
    quota_exceeded: bool = False
    job_name: str = ""

    @property
    def succeeded(self) -> bool:
        if self.quota_exceeded:
            return False
        return self.result.success if self.result is not None else False


class QuotaExecutor:
    """Runs a job only if its quota has not been exceeded.

    Records a successful execution against the quota window so that
    subsequent calls are counted correctly.
    """

    def __init__(self, inner: _InnerExecutor, tracker: QuotaTracker) -> None:
        self._inner = inner
        self._tracker = tracker

    def run(self, job) -> QuotaResult:
        name: str = job.name
        now = datetime.now(timezone.utc)
        try:
            self._tracker.check(name, now=now)
        except QuotaExceededError:
            return QuotaResult(result=None, quota_exceeded=True, job_name=name)

        result = self._inner.run(job)

        if result.success:
            self._tracker.record(name, now=now)

        return QuotaResult(result=result, quota_exceeded=False, job_name=name)


def build_quota_executor(
    inner: _InnerExecutor,
    policy: Optional[QuotaPolicy] = None,
) -> QuotaExecutor:
    """Convenience factory."""
    if policy is None:
        policy = QuotaPolicy()
    return QuotaExecutor(inner, QuotaTracker(policy))
