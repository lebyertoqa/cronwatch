"""Job annotation support: attach arbitrary key/value metadata to jobs."""
from __future__ import annotations

from typing import Any


def annotations_for(job: Any) -> dict[str, Any]:
    """Return the annotations dict for *job*, or an empty dict if none are set."""
    raw = getattr(job, "annotations", None)
    if not isinstance(raw, dict):
        return {}
    return dict(raw)


def get_annotation(job: Any, key: str, default: Any = None) -> Any:
    """Return the value of a single annotation *key*, or *default*."""
    return annotations_for(job).get(key, default)


def has_annotation(job: Any, key: str) -> bool:
    """Return True if *job* has an annotation with the given *key*."""
    return key in annotations_for(job)


def jobs_with_annotation(jobs: list[Any], key: str) -> list[Any]:
    """Filter *jobs* to those that carry annotation *key*."""
    return [j for j in jobs if has_annotation(j, key)]


def jobs_with_annotation_value(jobs: list[Any], key: str, value: Any) -> list[Any]:
    """Filter *jobs* to those whose annotation *key* equals *value*."""
    return [j for j in jobs if get_annotation(j, key) == value]


def all_annotation_keys(jobs: list[Any]) -> set[str]:
    """Return the union of all annotation keys across *jobs*."""
    keys: set[str] = set()
    for job in jobs:
        keys.update(annotations_for(job).keys())
    return keys


def annotate(job: Any, key: str, value: Any) -> None:
    """Set annotation *key* to *value* on *job* in-place.

    The job object must have a mutable ``annotations`` attribute (dict).
    If the attribute is missing or None it is initialised to an empty dict.
    """
    if not isinstance(getattr(job, "annotations", None), dict):
        job.annotations = {}
    job.annotations[key] = value
