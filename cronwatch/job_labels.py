"""Attach arbitrary key/value labels to jobs and query by them."""
from __future__ import annotations

from typing import Dict, Iterable, List

from cronwatch.config import JobConfig


def labels_for(job: JobConfig) -> Dict[str, str]:
    """Return the labels dict for *job*, defaulting to an empty dict."""
    return dict(getattr(job, "labels", None) or {})


def jobs_with_label(jobs: Iterable[JobConfig], key: str) -> List[JobConfig]:
    """Return jobs that have the label *key* (any value)."""
    return [j for j in jobs if key in labels_for(j)]


def jobs_with_label_value(
    jobs: Iterable[JobConfig], key: str, value: str
) -> List[JobConfig]:
    """Return jobs whose label *key* equals *value*."""
    return [j for j in jobs if labels_for(j).get(key) == value]


def all_label_keys(jobs: Iterable[JobConfig]) -> List[str]:
    """Return a sorted, deduplicated list of every label key in use."""
    keys: set[str] = set()
    for job in jobs:
        keys.update(labels_for(job).keys())
    return sorted(keys)


def jobs_matching_labels(
    jobs: Iterable[JobConfig], required: Dict[str, str]
) -> List[JobConfig]:
    """Return jobs that carry *all* key=value pairs in *required*."""
    if not required:
        return list(jobs)
    result = []
    for job in jobs:
        lbls = labels_for(job)
        if all(lbls.get(k) == v for k, v in required.items()):
            result.append(job)
    return result
