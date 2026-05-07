"""Filter jobs by tag, name pattern, or enabled state."""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from cronwatch.config import JobConfig


@dataclass
class JobFilter:
    """Criteria used to select a subset of configured jobs."""

    tags: List[str] = field(default_factory=list)
    name_pattern: Optional[str] = None
    enabled_only: bool = True

    def matches(self, job: JobConfig) -> bool:
        """Return True when *job* satisfies every active criterion."""
        if self.enabled_only and not getattr(job, "enabled", True):
            return False

        if self.name_pattern and not fnmatch.fnmatch(job.name, self.name_pattern):
            return False

        if self.tags:
            job_tags: List[str] = getattr(job, "tags", []) or []
            if not any(t in job_tags for t in self.tags):
                return False

        return True


def apply_filter(
    jobs: Iterable[JobConfig],
    job_filter: JobFilter,
) -> List[JobConfig]:
    """Return only the jobs that satisfy *job_filter*."""
    return [j for j in jobs if job_filter.matches(j)]
