"""Attach, retrieve, and query arbitrary metadata on job configs."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def metadata_for(job) -> Dict[str, Any]:
    """Return a shallow copy of the metadata dict for *job*.

    Returns an empty dict when the job has no ``metadata`` attribute or
    when it is ``None``.
    """
    raw = getattr(job, "metadata", None)
    if not isinstance(raw, dict):
        return {}
    return dict(raw)


def get_meta(job, key: str, default: Any = None) -> Any:
    """Return the value for *key* in the job's metadata, or *default*."""
    return metadata_for(job).get(key, default)


def has_meta(job, key: str) -> bool:
    """Return ``True`` when *key* is present in the job's metadata."""
    return key in metadata_for(job)


def jobs_with_meta(jobs: List, key: str) -> List:
    """Filter *jobs* to those that have *key* in their metadata."""
    return [j for j in jobs if has_meta(j, key)]


def jobs_with_meta_value(jobs: List, key: str, value: Any) -> List:
    """Filter *jobs* to those whose metadata[*key*] == *value*."""
    return [j for j in jobs if get_meta(j, key) is not None and get_meta(j, key) == value]


def all_meta_keys(jobs: List) -> List[str]:
    """Return a sorted, deduplicated list of every metadata key across *jobs*."""
    keys: set = set()
    for job in jobs:
        keys.update(metadata_for(job).keys())
    return sorted(keys)


def jobs_matching_metadata(jobs: List, criteria: Dict[str, Any]) -> List:
    """Return jobs whose metadata contains *all* key/value pairs in *criteria*."""
    result = []
    for job in jobs:
        meta = metadata_for(job)
        if all(meta.get(k) == v for k, v in criteria.items()):
            result.append(job)
    return result
