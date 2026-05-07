"""Tests for cronwatch.job_tags."""
from __future__ import annotations

import pytest

from cronwatch.config import JobConfig
from cronwatch.job_tags import (
    all_tags,
    jobs_matching_all,
    jobs_matching_any,
    jobs_with_tag,
    tags_for,
)


def _job(name: str, tags: list[str] | None = None) -> JobConfig:
    return JobConfig(
        name=name,
        command=f"echo {name}",
        schedule="* * * * *",
        tags=tags or [],
    )


def test_tags_for_returns_empty_set_when_no_tags():
    job = _job("noop")
    assert tags_for(job) == set()


def test_tags_for_returns_correct_tags():
    job = _job("backup", tags=["db", "nightly"])
    assert tags_for(job) == {"db", "nightly"}


def test_jobs_with_tag_filters_correctly():
    jobs = [
        _job("a", tags=["db"]),
        _job("b", tags=["web"]),
        _job("c", tags=["db", "web"]),
    ]
    result = jobs_with_tag(jobs, "db")
    assert [j.name for j in result] == ["a", "c"]


def test_jobs_with_tag_returns_empty_when_no_match():
    jobs = [_job("a", tags=["web"]), _job("b")]
    assert jobs_with_tag(jobs, "db") == []


def test_all_tags_returns_union():
    jobs = [
        _job("a", tags=["db", "nightly"]),
        _job("b", tags=["web"]),
        _job("c"),
    ]
    assert all_tags(jobs) == {"db", "nightly", "web"}


def test_all_tags_empty_when_no_jobs():
    assert all_tags([]) == set()


def test_jobs_matching_any_returns_union_of_tag_matches():
    jobs = [
        _job("a", tags=["db"]),
        _job("b", tags=["web"]),
        _job("c", tags=["cache"]),
    ]
    result = jobs_matching_any(jobs, ["db", "web"])
    assert [j.name for j in result] == ["a", "b"]


def test_jobs_matching_any_empty_tags_returns_all():
    jobs = [_job("a", tags=["db"]), _job("b")]
    assert jobs_matching_any(jobs, []) == jobs


def test_jobs_matching_all_requires_all_tags_present():
    jobs = [
        _job("a", tags=["db", "nightly"]),
        _job("b", tags=["db"]),
        _job("c", tags=["nightly"]),
    ]
    result = jobs_matching_all(jobs, ["db", "nightly"])
    assert [j.name for j in result] == ["a"]


def test_jobs_matching_all_empty_tags_returns_all():
    jobs = [_job("a", tags=["db"]), _job("b")]
    assert jobs_matching_all(jobs, []) == jobs
