"""High-level helper that builds a JobFilter from CLI / config arguments."""
from __future__ import annotations

from typing import List, Optional

from cronwatch.config import CronwatchConfig, JobConfig
from cronwatch.job_filter import JobFilter, apply_filter


def select_jobs(
    config: CronwatchConfig,
    *,
    tags: Optional[List[str]] = None,
    name_pattern: Optional[str] = None,
    include_disabled: bool = False,
) -> List[JobConfig]:
    """Return jobs from *config* that match the supplied selection criteria.

    Parameters
    ----------
    config:
        The loaded :class:`CronwatchConfig`.
    tags:
        When provided, only jobs whose ``tags`` list contains at least one
        of these values are returned.
    name_pattern:
        Shell-style glob pattern matched against ``job.name``.
    include_disabled:
        When *True*, disabled jobs are included in the result.
    """
    job_filter = JobFilter(
        tags=tags or [],
        name_pattern=name_pattern,
        enabled_only=not include_disabled,
    )
    return apply_filter(config.jobs, job_filter)
