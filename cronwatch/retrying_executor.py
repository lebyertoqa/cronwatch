"""Executor wrapper that applies a RetryPolicy around job execution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from cronwatch.config import JobConfig
from cronwatch.executor import ExecutionResult, run_job
from cronwatch.job_retry import RetryPolicy, RetryResult, build_retry_policy, with_retry


@dataclass
class RetryingExecutor:
    """Wraps a low-level runner with retry logic.

    Parameters
    ----------
    policy:
        The :class:`~cronwatch.job_retry.RetryPolicy` to apply.
    runner:
        Callable that executes a single attempt; defaults to
        :func:`~cronwatch.executor.run_job`.
    """

    policy: RetryPolicy
    runner: Callable[[JobConfig], ExecutionResult] = run_job

    def run(self, job: JobConfig) -> RetryResult:
        """Execute *job* with retries as configured by *policy*."""
        return with_retry(job, self.policy, self.runner)


def build_retrying_executor(
    retry_cfg: dict,
    runner: Callable[[JobConfig], ExecutionResult] = run_job,
) -> RetryingExecutor:
    """Convenience factory used by the application bootstrap.

    Parameters
    ----------
    retry_cfg:
        Raw dict from the YAML config (``retry:`` block).
    runner:
        Underlying single-attempt executor; defaults to
        :func:`~cronwatch.executor.run_job`.
    """
    policy = build_retry_policy(retry_cfg)
    return RetryingExecutor(policy=policy, runner=runner)
