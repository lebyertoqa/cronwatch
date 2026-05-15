"""Group jobs by arbitrary attributes for reporting and dispatch."""
from __future__ import annotations

from collections import defaultdict
from typing import Callable, Dict, List, Optional

from cronwatch.config import JobConfig


def group_by(jobs: List[JobConfig], key: Callable[[JobConfig], str]) -> Dict[str, List[JobConfig]]:
    """Partition *jobs* into buckets using *key*."""
    groups: Dict[str, List[JobConfig]] = defaultdict(list)
    for job in jobs:
        groups[key(job)].append(job)
    return dict(groups)


def group_by_tag(jobs: List[JobConfig]) -> Dict[str, List[JobConfig]]:
    """Return one bucket per tag; jobs with multiple tags appear in each."""
    groups: Dict[str, List[JobConfig]] = defaultdict(list)
    for job in jobs:
        tags = getattr(job, "tags", None) or []
        for tag in tags:
            groups[tag].append(job)
    return dict(groups)


def group_by_label(jobs: List[JobConfig], label_key: str) -> Dict[str, List[JobConfig]]:
    """Bucket jobs by the value of a specific label; jobs missing the label go into ''."""
    groups: Dict[str, List[JobConfig]] = defaultdict(list)
    for job in jobs:
        labels = getattr(job, "labels", None) or {}
        value = labels.get(label_key, "")
        groups[str(value)].append(job)
    return dict(groups)


def group_by_schedule(jobs: List[JobConfig]) -> Dict[str, List[JobConfig]]:
    """Bucket jobs by their cron schedule string."""
    return group_by(jobs, lambda j: getattr(j, "schedule", "") or "")


def flatten_groups(groups: Dict[str, List[JobConfig]]) -> List[JobConfig]:
    """Return a deduplicated flat list preserving first-seen order."""
    seen: set = set()
    result: List[JobConfig] = []
    for bucket in groups.values():
        for job in bucket:
            job_id = id(job)
            if job_id not in seen:
                seen.add(job_id)
                result.append(job)
    return result


def largest_group(groups: Dict[str, List[JobConfig]]) -> Optional[str]:
    """Return the key of the group with the most jobs, or None if empty."""
    if not groups:
        return None
    return max(groups, key=lambda k: len(groups[k]))
