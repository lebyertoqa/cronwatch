"""Tests for cronwatch.job_priority."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronwatch.job_priority import (
    DEFAULT_PRIORITY,
    filter_by_min_priority,
    group_by_priority,
    highest_priority,
    priority_of,
    sort_by_priority,
)


def _job(name: str, priority: int | None = None) -> MagicMock:
    job = MagicMock()
    job.name = name
    job.priority = priority
    return job


# ---------------------------------------------------------------------------
# priority_of
# ---------------------------------------------------------------------------

def test_priority_of_returns_set_value():
    assert priority_of(_job("a", 10)) == 10


def test_priority_of_falls_back_to_default_when_none():
    assert priority_of(_job("a", None)) == DEFAULT_PRIORITY


def test_priority_of_falls_back_when_attribute_missing():
    job = MagicMock(spec=["name"])  # no 'priority' attribute
    job.name = "no-prio"
    assert priority_of(job) == DEFAULT_PRIORITY


# ---------------------------------------------------------------------------
# sort_by_priority
# ---------------------------------------------------------------------------

def test_sort_descending_highest_first():
    jobs = [_job("low", 1), _job("high", 9), _job("mid", 5)]
    result = sort_by_priority(jobs)
    assert [j.name for j in result] == ["high", "mid", "low"]


def test_sort_ascending():
    jobs = [_job("low", 1), _job("high", 9), _job("mid", 5)]
    result = sort_by_priority(jobs, descending=False)
    assert [j.name for j in result] == ["low", "mid", "high"]


def test_sort_empty_list_returns_empty():
    assert sort_by_priority([]) == []


def test_sort_does_not_mutate_original():
    jobs = [_job("a", 3), _job("b", 1)]
    original_order = [j.name for j in jobs]
    sort_by_priority(jobs)
    assert [j.name for j in jobs] == original_order


# ---------------------------------------------------------------------------
# group_by_priority
# ---------------------------------------------------------------------------

def test_group_by_priority_basic():
    jobs = [_job("a", 5), _job("b", 1), _job("c", 5)]
    groups = group_by_priority(jobs)
    assert list(groups.keys()) == [5, 1]
    assert {j.name for j in groups[5]} == {"a", "c"}
    assert {j.name for j in groups[1]} == {"b"}


def test_group_by_priority_empty():
    assert group_by_priority([]) == {}


def test_group_by_priority_single_group():
    jobs = [_job("x", 3), _job("y", 3)]
    groups = group_by_priority(jobs)
    assert list(groups.keys()) == [3]


# ---------------------------------------------------------------------------
# highest_priority
# ---------------------------------------------------------------------------

def test_highest_priority_returns_max():
    jobs = [_job("a", 2), _job("b", 7), _job("c", 4)]
    assert highest_priority(jobs) == 7


def test_highest_priority_empty_returns_default():
    assert highest_priority([]) == DEFAULT_PRIORITY


# ---------------------------------------------------------------------------
# filter_by_min_priority
# ---------------------------------------------------------------------------

def test_filter_keeps_jobs_at_or_above_min():
    jobs = [_job("a", 1), _job("b", 5), _job("c", 10)]
    result = filter_by_min_priority(jobs, 5)
    assert {j.name for j in result} == {"b", "c"}


def test_filter_returns_empty_when_none_qualify():
    jobs = [_job("a", 1), _job("b", 2)]
    assert filter_by_min_priority(jobs, 99) == []


def test_filter_returns_all_when_min_is_zero():
    jobs = [_job("a", 0), _job("b", 5)]
    assert len(filter_by_min_priority(jobs, 0)) == 2
