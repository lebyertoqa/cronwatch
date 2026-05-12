"""Tests for cronwatch.job_annotations."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from cronwatch.job_annotations import (
    all_annotation_keys,
    annotate,
    annotations_for,
    get_annotation,
    has_annotation,
    jobs_with_annotation,
    jobs_with_annotation_value,
)


def _job(**kwargs: Any) -> SimpleNamespace:
    return SimpleNamespace(**kwargs)


# ---------------------------------------------------------------------------
# annotations_for
# ---------------------------------------------------------------------------

def test_annotations_for_returns_empty_when_none():
    job = _job()
    assert annotations_for(job) == {}


def test_annotations_for_returns_empty_when_not_dict():
    job = _job(annotations="not-a-dict")
    assert annotations_for(job) == {}


def test_annotations_for_returns_copy():
    job = _job(annotations={"team": "ops"})
    result = annotations_for(job)
    result["extra"] = "x"
    assert "extra" not in job.annotations


def test_annotations_for_returns_correct_mapping():
    job = _job(annotations={"owner": "alice", "env": "prod"})
    assert annotations_for(job) == {"owner": "alice", "env": "prod"}


# ---------------------------------------------------------------------------
# get_annotation / has_annotation
# ---------------------------------------------------------------------------

def test_get_annotation_returns_value():
    job = _job(annotations={"tier": "critical"})
    assert get_annotation(job, "tier") == "critical"


def test_get_annotation_returns_default_when_missing():
    job = _job(annotations={"tier": "critical"})
    assert get_annotation(job, "owner", "unknown") == "unknown"


def test_has_annotation_true():
    job = _job(annotations={"notify": True})
    assert has_annotation(job, "notify") is True


def test_has_annotation_false():
    job = _job(annotations={})
    assert has_annotation(job, "notify") is False


# ---------------------------------------------------------------------------
# jobs_with_annotation / jobs_with_annotation_value
# ---------------------------------------------------------------------------

def test_jobs_with_annotation_filters_correctly():
    jobs = [
        _job(name="a", annotations={"team": "ops"}),
        _job(name="b", annotations={"owner": "bob"}),
        _job(name="c", annotations={"team": "dev"}),
    ]
    result = jobs_with_annotation(jobs, "team")
    assert [j.name for j in result] == ["a", "c"]


def test_jobs_with_annotation_returns_empty_when_no_match():
    jobs = [_job(name="a", annotations={"x": 1})]
    assert jobs_with_annotation(jobs, "missing") == []


def test_jobs_with_annotation_value_exact_match():
    jobs = [
        _job(name="a", annotations={"env": "prod"}),
        _job(name="b", annotations={"env": "staging"}),
        _job(name="c", annotations={"env": "prod"}),
    ]
    result = jobs_with_annotation_value(jobs, "env", "prod")
    assert [j.name for j in result] == ["a", "c"]


def test_jobs_with_annotation_value_no_match():
    jobs = [_job(name="a", annotations={"env": "staging"})]
    assert jobs_with_annotation_value(jobs, "env", "prod") == []


# ---------------------------------------------------------------------------
# all_annotation_keys
# ---------------------------------------------------------------------------

def test_all_annotation_keys_union():
    jobs = [
        _job(annotations={"team": "ops", "env": "prod"}),
        _job(annotations={"owner": "alice", "env": "staging"}),
    ]
    assert all_annotation_keys(jobs) == {"team", "env", "owner"}


def test_all_annotation_keys_empty_jobs():
    assert all_annotation_keys([]) == set()


# ---------------------------------------------------------------------------
# annotate (mutates in-place)
# ---------------------------------------------------------------------------

def test_annotate_sets_value():
    job = _job(annotations={"existing": 1})
    annotate(job, "new_key", "hello")
    assert job.annotations["new_key"] == "hello"


def test_annotate_creates_dict_when_missing():
    job = _job()
    annotate(job, "owner", "bob")
    assert job.annotations == {"owner": "bob"}


def test_annotate_overwrites_existing():
    job = _job(annotations={"env": "staging"})
    annotate(job, "env", "prod")
    assert job.annotations["env"] == "prod"
