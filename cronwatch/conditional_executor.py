"""Executor wrapper that skips a job when its pre-conditions are not met."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from cronwatch.config import JobConfig
from cronwatch.executor import ExecutionResult
from cronwatch.job_conditions import ConditionCheck, check_conditions


@dataclass
class ConditionalResult:
    """Wraps an ExecutionResult or records a skip caused by a condition failure."""
    job_name: str
    skipped: bool
    skip_reason: Optional[str]
    execution_result: Optional[ExecutionResult]
    condition_check: Optional[ConditionCheck]

    @property
    def succeeded(self) -> bool:
        if self.skipped:
            return False
        return self.execution_result is not None and self.execution_result.success


class ConditionalExecutor:
    """Runs a job only when all conditions pass; otherwise returns a skip result."""

    def __init__(self, inner, condition_timeout: int = 10) -> None:
        """
        Parameters
        ----------
        inner:
            An object with a ``run(job)`` method that returns an
            ``ExecutionResult``.
        condition_timeout:
            Seconds before an individual condition command times out.
        """
        self._inner = inner
        self._condition_timeout = condition_timeout

    def run(self, job: JobConfig) -> ConditionalResult:
        check = check_conditions(job, timeout=self._condition_timeout)
        if not check.all_passed:
            failure = check.first_failure
            reason = (
                f"condition failed (exit {failure.returncode}): {failure.command}"
                if failure
                else "condition check failed"
            )
            return ConditionalResult(
                job_name=job.name,
                skipped=True,
                skip_reason=reason,
                execution_result=None,
                condition_check=check,
            )

        result = self._inner.run(job)
        return ConditionalResult(
            job_name=job.name,
            skipped=False,
            skip_reason=None,
            execution_result=result,
            condition_check=check,
        )


def build_conditional_executor(inner, condition_timeout: int = 10) -> ConditionalExecutor:
    """Factory that wraps *inner* with condition-checking."""
    return ConditionalExecutor(inner, condition_timeout=condition_timeout)
