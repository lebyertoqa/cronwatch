"""Tests for cronwatch.job_grouping."""
from __future__ import annotations

from types import SimpleNamespace
from typing import List, Optional

import pytest

from cronwatch.job_grouping import (
    flatten_groups,
    group_by,
    group_by_label,
    group_by_schedule,
    group_by_tag,
    largest_group,
)


def _job(
    name: str,
    schedule: str = "* * * * *",
    tags: Optional[List[str]] = None,
    labels: Optional[dict] = None,
    enabled: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        schedule=schedule,
        tags=tags or [],
        labels=labels or {},
        enabled=enabled,
    )


# ---------------------------------------------------------------------------
# group_by
# ---------------------------------------------------------------------------

def test_group_by_partitions_correctly():
    jobs = [_job("a", schedule="0 * * * *"), _job("b", schedule="0 * * * *"), _job("c", schedule="5 * * * *")]
    groups = group_by(jobs, lambda j: j.schedule)
    assert set(groups.keys()) == {"0 * * * *", "5 * * * *"}
    assert len(groups["0 * * * *"]) == 2
    assert len(groups["5 * * * *"]) == 1


def test_group_by_empty_list():
    assert group_by([], lambda j: j.name) == {}


# ---------------------------------------------------------------------------
# group_by_tag
# ---------------------------------------------------------------------------

def test_group_by_tag_single_tag():
    jobs = [_job("a", tags=["nightly"]), _job("b", tags=["daily"])]
    groups = group_by_tag(jobs)
    assert "nightly" in groups
    assert groups["nightly"] == [jobs[0]]
    assert groups["daily"] == [jobs[1]]


def test_group_by_tag_multi_tag_job_appears_in_each():
    job = _job("a", tags=["x", "y"])
    groups = group_by_tag([job])
    assert job in groups["x"]
    assert job in groups["y"]


def test_group_by_tag_no_tags_returns_empty():
    jobs = [_job("a"), _job("b")]
    assert group_by_tag(jobs) == {}


# ---------------------------------------------------------------------------
# group_by_label
# ---------------------------------------------------------------------------

def test_group_by_label_buckets_by_value():
    jobs = [
        _job("a", labels={"env": "prod"}),
        _job("b", labels={"env": "staging"}),
        _job("c", labels={"env": "prod"}),
    ]
    groups = group_by_label(jobs, "env")
    assert len(groups["prod"]) == 2
    assert len(groups["staging"]) == 1


def test_group_by_label_missing_label_goes_to_empty_string():
    jobs = [_job("a"), _job("b", labels={"env": "prod"})]
    groups = group_by_label(jobs, "env")
    assert jobs[0] in groups[""]
    assert jobs[1] in groups["prod"]


# ---------------------------------------------------------------------------
# group_by_schedule
# ---------------------------------------------------------------------------

def test_group_by_schedule_uses_schedule_field():
    jobs = [_job("a", schedule="@daily"), _job("b", schedule="@daily"), _job("c", schedule="@hourly")]
    groups = group_by_schedule(jobs)
    assert len(groups["@daily"]) == 2
    assert len(groups["@hourly"]) == 1


# ---------------------------------------------------------------------------
# flatten_groups
# ---------------------------------------------------------------------------

def test_flatten_groups_deduplicates():
    job = _job("shared", tags=["x", "y"])
    groups = group_by_tag([job])
    flat = flatten_groups(groups)
    assert flat.count(job) == 1


def test_flatten_groups_preserves_all_unique():
    jobs = [_job("a"), _job("b"), _job("c")]
    groups = {"g1": jobs[:2], "g2": jobs[1:]}
    flat = flatten_groups(groups)
    assert set(flat) == set(jobs)


# ---------------------------------------------------------------------------
# largest_group
# ---------------------------------------------------------------------------

def test_largest_group_returns_key_with_most_jobs():
    jobs = [_job("a"), _job("b"), _job("c")]
    groups = {"small": jobs[:1], "big": jobs}
    assert largest_group(groups) == "big"


def test_largest_group_returns_none_for_empty():
    assert largest_group({}) is None
