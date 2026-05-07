"""Tests for cronwatch.job_labels."""
from __future__ import annotations

import pytest

from cronwatch.config import JobConfig
from cronwatch.job_labels import (
    all_label_keys,
    jobs_matching_labels,
    jobs_with_label,
    jobs_with_label_value,
    labels_for,
)


def _job(name: str, labels: dict | None = None) -> JobConfig:
    return JobConfig(
        name=name,
        command="echo hi",
        schedule="* * * * *",
        labels=labels,
    )


# ---------------------------------------------------------------------------
# labels_for
# ---------------------------------------------------------------------------

def test_labels_for_returns_empty_dict_when_none():
    job = _job("a")
    assert labels_for(job) == {}


def test_labels_for_returns_correct_mapping():
    job = _job("b", {"env": "prod", "team": "ops"})
    assert labels_for(job) == {"env": "prod", "team": "ops"}


def test_labels_for_returns_copy():
    job = _job("c", {"x": "1"})
    copy = labels_for(job)
    copy["y"] = "2"
    assert "y" not in labels_for(job)


# ---------------------------------------------------------------------------
# jobs_with_label
# ---------------------------------------------------------------------------

def test_jobs_with_label_returns_matching():
    jobs = [_job("a", {"env": "prod"}), _job("b"), _job("c", {"env": "dev"})]
    result = jobs_with_label(jobs, "env")
    assert [j.name for j in result] == ["a", "c"]


def test_jobs_with_label_returns_empty_when_none_match():
    jobs = [_job("a"), _job("b")]
    assert jobs_with_label(jobs, "missing") == []


# ---------------------------------------------------------------------------
# jobs_with_label_value
# ---------------------------------------------------------------------------

def test_jobs_with_label_value_filters_correctly():
    jobs = [
        _job("a", {"env": "prod"}),
        _job("b", {"env": "dev"}),
        _job("c", {"env": "prod"}),
    ]
    result = jobs_with_label_value(jobs, "env", "prod")
    assert [j.name for j in result] == ["a", "c"]


def test_jobs_with_label_value_no_match():
    jobs = [_job("a", {"env": "dev"})]
    assert jobs_with_label_value(jobs, "env", "prod") == []


# ---------------------------------------------------------------------------
# all_label_keys
# ---------------------------------------------------------------------------

def test_all_label_keys_returns_sorted_unique():
    jobs = [
        _job("a", {"team": "ops", "env": "prod"}),
        _job("b", {"env": "dev", "region": "eu"}),
    ]
    assert all_label_keys(jobs) == ["env", "region", "team"]


def test_all_label_keys_empty_when_no_labels():
    assert all_label_keys([_job("a"), _job("b")]) == []


# ---------------------------------------------------------------------------
# jobs_matching_labels
# ---------------------------------------------------------------------------

def test_jobs_matching_labels_all_required_present():
    jobs = [
        _job("a", {"env": "prod", "team": "ops"}),
        _job("b", {"env": "prod", "team": "dev"}),
        _job("c", {"env": "prod"}),
    ]
    result = jobs_matching_labels(jobs, {"env": "prod", "team": "ops"})
    assert [j.name for j in result] == ["a"]


def test_jobs_matching_labels_empty_required_returns_all():
    jobs = [_job("a"), _job("b")]
    assert len(jobs_matching_labels(jobs, {})) == 2


def test_jobs_matching_labels_no_match():
    jobs = [_job("a", {"env": "dev"})]
    assert jobs_matching_labels(jobs, {"env": "prod"}) == []
