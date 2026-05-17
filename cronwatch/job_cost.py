"""Track and report estimated execution cost per job."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CostEntry:
    job_name: str
    duration_seconds: float
    cost_per_second: float

    @property
    def estimated_cost(self) -> float:
        return self.duration_seconds * self.cost_per_second


@dataclass
class CostPolicy:
    default_cost_per_second: float = 0.0
    per_job: Dict[str, float] = field(default_factory=dict)

    def rate_for(self, job_name: str) -> float:
        return self.per_job.get(job_name, self.default_cost_per_second)


@dataclass
class CostSummary:
    job_name: str
    total_cost: float
    total_runs: int
    total_seconds: float

    @property
    def average_cost(self) -> Optional[float]:
        if self.total_runs == 0:
            return None
        return self.total_cost / self.total_runs


class CostTracker:
    def __init__(self, policy: CostPolicy) -> None:
        self._policy = policy
        self._entries: List[CostEntry] = []

    def record(self, job_name: str, duration_seconds: float) -> CostEntry:
        rate = self._policy.rate_for(job_name)
        entry = CostEntry(
            job_name=job_name,
            duration_seconds=duration_seconds,
            cost_per_second=rate,
        )
        self._entries.append(entry)
        return entry

    def entries_for(self, job_name: str) -> List[CostEntry]:
        return [e for e in self._entries if e.job_name == job_name]

    def summarise(self, job_name: str) -> CostSummary:
        entries = self.entries_for(job_name)
        total_cost = sum(e.estimated_cost for e in entries)
        total_seconds = sum(e.duration_seconds for e in entries)
        return CostSummary(
            job_name=job_name,
            total_cost=total_cost,
            total_runs=len(entries),
            total_seconds=total_seconds,
        )

    def all_summaries(self) -> List[CostSummary]:
        names = {e.job_name for e in self._entries}
        return [self.summarise(name) for name in sorted(names)]

    def total_cost(self) -> float:
        return sum(e.estimated_cost for e in self._entries)
