"""Retry policy for failed cron jobs."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from cronwatch.config import JobConfig
from cronwatch.executor import ExecutionResult


@dataclass
class RetryPolicy:
    """Describes how many times and how often to retry a job."""
    default_attempts: int = 1
    default_delay: float = 5.0          # seconds between attempts
    default_backoff: float = 1.0        # multiplier applied after each failure
    per_job: dict[str, dict] = field(default_factory=dict)

    def attempts_for(self, job_name: str) -> int:
        override = self.per_job.get(job_name, {})
        return int(override.get("attempts", self.default_attempts))

    def delay_for(self, job_name: str) -> float:
        override = self.per_job.get(job_name, {})
        return float(override.get("delay", self.default_delay))

    def backoff_for(self, job_name: str) -> float:
        override = self.per_job.get(job_name, {})
        return float(override.get("backoff", self.default_backoff))


@dataclass
class RetryResult:
    """Outcome of a (possibly retried) job execution."""
    final: ExecutionResult
    attempts: int
    succeeded: bool

    @property
    def retried(self) -> bool:
        """Return True if the job was attempted more than once."""
        return self.attempts > 1


def with_retry(
    job: JobConfig,
    policy: RetryPolicy,
    runner: Callable[[JobConfig], ExecutionResult],
    sleep: Callable[[float], None] = time.sleep,
) -> RetryResult:
    """Run *runner* up to policy.attempts_for(job.name) times.

    Returns a :class:`RetryResult` containing the last
    :class:`ExecutionResult` and metadata about how many attempts were made.
    """
    max_attempts = max(1, policy.attempts_for(job.name))
    delay = policy.delay_for(job.name)
    backoff = policy.backoff_for(job.name)

    result: Optional[ExecutionResult] = None
    for attempt in range(1, max_attempts + 1):
        result = runner(job)
        if result.success:
            return RetryResult(final=result, attempts=attempt, succeeded=True)
        if attempt < max_attempts:
            sleep(delay)
            delay *= backoff

    assert result is not None
    return RetryResult(final=result, attempts=max_attempts, succeeded=False)


def build_retry_policy(cfg: dict) -> RetryPolicy:
    """Build a :class:`RetryPolicy` from a plain config dict."""
    return RetryPolicy(
        default_attempts=int(cfg.get("default_attempts", 1)),
        default_delay=float(cfg.get("default_delay", 5.0)),
        default_backoff=float(cfg.get("default_backoff", 1.0)),
        per_job=cfg.get("per_job", {}),
    )
