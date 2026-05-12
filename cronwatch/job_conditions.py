"""Conditional execution support for cron jobs.

A condition is a shell command that must exit 0 for a job to be allowed to run.
If any condition fails the job is skipped and a SkipResult is returned.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

from cronwatch.config import JobConfig


@dataclass
class ConditionResult:
    """Outcome of evaluating a single pre-condition command."""
    command: str
    passed: bool
    returncode: int
    stderr: str = ""

    @property
    def failed(self) -> bool:
        return not self.passed


@dataclass
class ConditionCheck:
    """Aggregate result of evaluating all conditions for a job."""
    job_name: str
    results: List[ConditionResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def first_failure(self) -> Optional[ConditionResult]:
        for r in self.results:
            if r.failed:
                return r
        return None


def conditions_for(job: JobConfig) -> List[str]:
    """Return the list of condition commands configured for *job*."""
    return list(getattr(job, "conditions", None) or [])


def evaluate_condition(command: str, timeout: int = 10) -> ConditionResult:
    """Run *command* in a shell and return a ConditionResult."""
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return ConditionResult(
            command=command,
            passed=proc.returncode == 0,
            returncode=proc.returncode,
            stderr=proc.stderr.strip(),
        )
    except subprocess.TimeoutExpired:
        return ConditionResult(
            command=command,
            passed=False,
            returncode=-1,
            stderr="condition timed out",
        )


def check_conditions(job: JobConfig, timeout: int = 10) -> ConditionCheck:
    """Evaluate all conditions for *job* and return a ConditionCheck."""
    check = ConditionCheck(job_name=job.name)
    for cmd in conditions_for(job):
        result = evaluate_condition(cmd, timeout=timeout)
        check.results.append(result)
        if result.failed:
            # Fail-fast: stop on first failing condition.
            break
    return check
