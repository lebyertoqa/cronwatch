"""Report job counts and summaries grouped by a metadata key."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from cronwatch.job_metadata import get_meta


@dataclass
class MetadataGroupSummary:
    key: str
    value: Any
    jobs: List = field(default_factory=list)

    @property
    def job_count(self) -> int:
        return len(self.jobs)

    @property
    def job_names(self) -> List[str]:
        return sorted(getattr(j, "name", str(j)) for j in self.jobs)


@dataclass
class MetadataReport:
    key: str
    groups: List[MetadataGroupSummary] = field(default_factory=list)

    @property
    def total_jobs(self) -> int:
        return sum(g.job_count for g in self.groups)

    def group_for(self, value: Any) -> MetadataGroupSummary | None:
        for g in self.groups:
            if g.value == value:
                return g
        return None

    def largest_group(self) -> MetadataGroupSummary | None:
        if not self.groups:
            return None
        return max(self.groups, key=lambda g: g.job_count)


class MetadataReporter:
    """Build a :class:`MetadataReport` by grouping jobs on a metadata key."""

    def __init__(self, jobs: List) -> None:
        self._jobs = jobs

    def report(self, key: str, default: Any = None) -> MetadataReport:
        """Group jobs by ``metadata[key]`` and return a :class:`MetadataReport`.

        Jobs that lack the key are placed under *default*.
        """
        buckets: Dict[Any, List] = {}
        for job in self._jobs:
            value = get_meta(job, key, default)
            buckets.setdefault(value, []).append(job)

        groups = [
            MetadataGroupSummary(key=key, value=v, jobs=js)
            for v, js in sorted(buckets.items(), key=lambda kv: str(kv[0]))
        ]
        return MetadataReport(key=key, groups=groups)
