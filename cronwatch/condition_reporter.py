"""Utilities for surfacing condition-skip events in reports and logs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from cronwatch.conditional_executor import ConditionalResult


@dataclass
class ConditionSkipSummary:
    """Aggregated skip statistics for a single job."""
    job_name: str
    skip_count: int = 0
    reasons: List[str] = field(default_factory=list)

    def record(self, reason: str) -> None:
        self.skip_count += 1
        self.reasons.append(reason)


class ConditionReporter:
    """Accumulates ConditionalResults and exposes skip summaries."""

    def __init__(self) -> None:
        self._summaries: Dict[str, ConditionSkipSummary] = {}

    def record(self, result: ConditionalResult) -> None:
        """Register a ConditionalResult; only skipped results are tracked."""
        if not result.skipped:
            return
        if result.job_name not in self._summaries:
            self._summaries[result.job_name] = ConditionSkipSummary(
                job_name=result.job_name
            )
        reason = result.skip_reason or "unknown"
        self._summaries[result.job_name].record(reason)

    def summary_for(self, job_name: str) -> ConditionSkipSummary:
        """Return the skip summary for *job_name* (empty if never skipped)."""
        return self._summaries.get(
            job_name, ConditionSkipSummary(job_name=job_name)
        )

    def all_summaries(self) -> List[ConditionSkipSummary]:
        """Return all summaries that have at least one skip."""
        return list(self._summaries.values())

    def total_skips(self) -> int:
        """Return the total number of skipped executions recorded."""
        return sum(s.skip_count for s in self._summaries.values())

    def jobs_skipped(self) -> List[str]:
        """Return names of jobs that were skipped at least once."""
        return list(self._summaries.keys())
