"""Tests for cronwatch.job_metadata."""
from __future__ import annotations

import types
from typing import Any, Dict, Optional

import pytest

from cronwatch.job_metadata import (
    all_meta_keys,
    get_meta,
    has_meta,
    jobs_matching_metadata,
    jobs_with_meta,
    jobs_with_meta_value,
    metadata_for,
)


def _job(name: str = "job", metadata: Optional[Dict[str, Any]] = None):
    j = types.SimpleNamespace(name=name)
    if metadata is not None:
        j.metadata = metadata
    return j


# ---------------------------------------------------------------------------
# metadata_for
# ---------------------------------------------------------------------------

def test_metadata_for_returns_empty_when_none():
    assert metadata_for(_job()) == {}


def test_metadata_for_returns_empty_when_not_dict():
    j = _job(metadata=None)  # type: ignore[arg-type]
    j.metadata = "bad"
    assert metadata_for(j) == {}


def test_metadata_for_returns_correct_mapping():
    j = _job(metadata={"owner": "alice", "team": "ops"})
    assert metadata_for(j) == {"owner": "alice", "team": "ops"}


def test_metadata_for_returns_copy():
    original = {"k": "v"}
    j = _job(metadata=original)
    copy = metadata_for(j)
    copy["extra"] = "x"
    assert "extra" not in original


# ---------------------------------------------------------------------------
# get_meta / has_meta
# ---------------------------------------------------------------------------

def test_get_meta_returns_value():
    j = _job(metadata={"env": "prod"})
    assert get_meta(j, "env") == "prod"


def test_get_meta_returns_default_when_missing():
    j = _job(metadata={"env": "prod"})
    assert get_meta(j, "owner", "unknown") == "unknown"


def test_get_meta_default_is_none():
    j = _job()
    assert get_meta(j, "missing") is None


def test_has_meta_true_when_present():
    j = _job(metadata={"critical": True})
    assert has_meta(j, "critical") is True


def test_has_meta_false_when_absent():
    j = _job(metadata={"critical": True})
    assert has_meta(j, "owner") is False


def test_has_meta_false_when_no_metadata():
    assert has_meta(_job(), "anything") is False


# ---------------------------------------------------------------------------
# jobs_with_meta / jobs_with_meta_value
# ---------------------------------------------------------------------------

def test_jobs_with_meta_filters_correctly():
    jobs = [
        _job("a", {"owner": "alice"}),
        _job("b", {}),
        _job("c", {"owner": "bob"}),
    ]
    assert [j.name for j in jobs_with_meta(jobs, "owner")] == ["a", "c"]


def test_jobs_with_meta_value_filters_correctly():
    jobs = [
        _job("a", {"env": "prod"}),
        _job("b", {"env": "staging"}),
        _job("c", {"env": "prod"}),
    ]
    assert [j.name for j in jobs_with_meta_value(jobs, "env", "prod")] == ["a", "c"]


def test_jobs_with_meta_value_excludes_missing_key():
    jobs = [_job("a", {}), _job("b", {"env": "prod"})]
    assert [j.name for j in jobs_with_meta_value(jobs, "env", "prod")] == ["b"]


# ---------------------------------------------------------------------------
# all_meta_keys
# ---------------------------------------------------------------------------

def test_all_meta_keys_sorted_and_deduped():
    jobs = [
        _job(metadata={"b": 1, "a": 2}),
        _job(metadata={"a": 3, "c": 4}),
    ]
    assert all_meta_keys(jobs) == ["a", "b", "c"]


def test_all_meta_keys_empty_when_no_metadata():
    assert all_meta_keys([_job(), _job()]) == []


# ---------------------------------------------------------------------------
# jobs_matching_metadata
# ---------------------------------------------------------------------------

def test_jobs_matching_metadata_all_criteria():
    jobs = [
        _job("a", {"env": "prod", "team": "ops"}),
        _job("b", {"env": "prod", "team": "dev"}),
        _job("c", {"env": "staging", "team": "ops"}),
    ]
    result = jobs_matching_metadata(jobs, {"env": "prod", "team": "ops"})
    assert [j.name for j in result] == ["a"]


def test_jobs_matching_metadata_empty_criteria_matches_all():
    jobs = [_job("a"), _job("b")]
    assert len(jobs_matching_metadata(jobs, {})) == 2
