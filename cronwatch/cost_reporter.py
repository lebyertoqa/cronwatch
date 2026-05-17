"""Generate cost reports across all tracked jobs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from cronwatch.job_cost import CostSummary, CostTracker


@dataclass
class CostReport:
    summaries: List[CostSummary]

    @property
    def total_jobs(self) -> int:
        return len(self.summaries)

    @property
    def grand_total_cost(self) -> float:
        return sum(s.total_cost for s in self.summaries)

    @property
    def most_expensive_job(self) -> Optional[CostSummary]:
        if not self.summaries:
            return None
        return max(self.summaries, key=lambda s: s.total_cost)

    @property
    def cheapest_job(self) -> Optional[CostSummary]:
        if not self.summaries:
            return None
        return min(self.summaries, key=lambda s: s.total_cost)

    def jobs_above_cost(self, threshold: float) -> List[CostSummary]:
        return [s for s in self.summaries if s.total_cost > threshold]


class CostReporter:
    def __init__(self, tracker: CostTracker) -> None:
        self._tracker = tracker

    def build_report(self) -> CostReport:
        summaries = self._tracker.all_summaries()
        return CostReport(summaries=summaries)

    def report_for_job(self, job_name: str) -> CostSummary:
        return self._tracker.summarise(job_name)
