"""Utilities for working with job tags."""
from __future__ import annotations

from typing import Iterable, Set

from cronwatch.config import JobConfig


def tags_for(job: JobConfig) -> Set[str]:
    """Return the set of tags for a job (empty set if none defined)."""
    return set(getattr(job, "tags", None) or [])


def jobs_with_tag(jobs: Iterable[JobConfig], tag: str) -> list[JobConfig]:
    """Return jobs that carry *tag*."""
    return [j for j in jobs if tag in tags_for(j)]


def all_tags(jobs: Iterable[JobConfig]) -> Set[str]:
    """Return the union of every tag used across *jobs*."""
    result: Set[str] = set()
    for job in jobs:
        result |= tags_for(job)
    return result


def jobs_matching_any(jobs: Iterable[JobConfig], tags: Iterable[str]) -> list[JobConfig]:
    """Return jobs whose tag set intersects with *tags*."""
    wanted = set(tags)
    if not wanted:
        return list(jobs)
    return [j for j in jobs if tags_for(j) & wanted]


def jobs_matching_all(jobs: Iterable[JobConfig], tags: Iterable[str]) -> list[JobConfig]:
    """Return jobs whose tag set is a superset of *tags*."""
    wanted = set(tags)
    if not wanted:
        return list(jobs)
    return [j for j in jobs if wanted <= tags_for(j)]
