"""Job priority ordering utilities.

Jobs can declare an integer `priority` field (higher = more important).
This module provides helpers to sort and group jobs by priority so the
dispatcher can run higher-priority jobs first when resources are limited.
"""
from __future__ import annotations

from typing import Iterable, List, Dict

from cronwatch.config import JobConfig

# Default priority assigned when a job does not specify one.
DEFAULT_PRIORITY: int = 0


def priority_of(job: JobConfig) -> int:
    """Return the numeric priority of *job*, falling back to DEFAULT_PRIORITY."""
    return getattr(job, "priority", DEFAULT_PRIORITY) or DEFAULT_PRIORITY


def sort_by_priority(jobs: Iterable[JobConfig], *, descending: bool = True) -> List[JobConfig]:
    """Return *jobs* sorted by priority.

    Args:
        jobs: Iterable of JobConfig objects.
        descending: When *True* (default) highest priority comes first.

    Returns:
        A new list sorted by priority.
    """
    return sorted(jobs, key=priority_of, reverse=descending)


def group_by_priority(jobs: Iterable[JobConfig]) -> Dict[int, List[JobConfig]]:
    """Partition *jobs* into a mapping of priority -> [job, ...].

    The returned dict is ordered from highest to lowest priority.
    """
    groups: Dict[int, List[JobConfig]] = {}
    for job in jobs:
        p = priority_of(job)
        groups.setdefault(p, []).append(job)
    return dict(sorted(groups.items(), reverse=True))


def highest_priority(jobs: Iterable[JobConfig]) -> int:
    """Return the maximum priority value present in *jobs*, or DEFAULT_PRIORITY."""
    job_list = list(jobs)
    if not job_list:
        return DEFAULT_PRIORITY
    return max(priority_of(j) for j in job_list)


def filter_by_min_priority(jobs: Iterable[JobConfig], min_priority: int) -> List[JobConfig]:
    """Return only jobs whose priority is >= *min_priority*."""
    return [j for j in jobs if priority_of(j) >= min_priority]
