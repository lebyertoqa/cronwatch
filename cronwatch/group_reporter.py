"""Produce per-group summaries from history entries."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List

from cronwatch.config import JobConfig
from cronwatch.history import HistoryEntry
from cronwatch.job_grouping import group_by


@dataclass
class GroupSummary:
    group_key: str
    total: int = 0
    failures: int = 0
    job_names: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 1.0
        return (self.total - self.failures) / self.total

    @property
    def has_failures(self) -> bool:
        return self.failures > 0


@dataclass
class GroupReport:
    summaries: Dict[str, GroupSummary] = field(default_factory=dict)

    def worst_group(self) -> str | None:
        """Return the group key with the lowest success rate, or None."""
        if not self.summaries:
            return None
        return min(self.summaries, key=lambda k: self.summaries[k].success_rate)


def build_group_report(
    jobs: List[JobConfig],
    entries: List[HistoryEntry],
    key_fn: Callable[[JobConfig], str],
) -> GroupReport:
    """Aggregate *entries* into a :class:`GroupReport` using *key_fn* to bucket jobs."""
    groups = group_by(jobs, key_fn)
    # Build name -> key mapping
    name_to_key: Dict[str, str] = {}
    for gkey, gjobs in groups.items():
        for job in gjobs:
            name_to_key[job.name] = gkey

    summaries: Dict[str, GroupSummary] = {}
    for gkey in groups:
        summaries[gkey] = GroupSummary(
            group_key=gkey,
            job_names=[j.name for j in groups[gkey]],
        )

    for entry in entries:
        gkey = name_to_key.get(entry.job_name)
        if gkey is None:
            continue
        summaries[gkey].total += 1
        if not entry.success:
            summaries[gkey].failures += 1

    return GroupReport(summaries=summaries)
