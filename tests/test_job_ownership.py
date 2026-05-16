"""Tests for cronwatch.job_ownership."""
from __future__ import annotations

from typing import Any, Dict, Optional

import pytest

from cronwatch.job_ownership import (
    OwnerInfo,
    all_teams,
    group_by_team,
    jobs_owned_by_team,
    jobs_without_owner,
    owner_for,
)


class _FakeJob:
    """Minimal stand-in for JobConfig."""

    def __init__(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.name = name
        self.metadata = metadata


def _job(name: str = "j", ownership: Optional[Dict] = None) -> _FakeJob:
    meta = {"ownership": ownership} if ownership is not None else {}
    return _FakeJob(name, meta)


# ---------------------------------------------------------------------------
# owner_for
# ---------------------------------------------------------------------------

def test_owner_for_returns_empty_when_no_metadata():
    j = _FakeJob("j", metadata=None)
    assert owner_for(j) == OwnerInfo()


def test_owner_for_returns_empty_when_no_ownership_key():
    j = _FakeJob("j", metadata={"labels": {"env": "prod"}})
    assert owner_for(j) == OwnerInfo()


def test_owner_for_extracts_team():
    j = _job(ownership={"team": "platform"})
    assert owner_for(j).team == "platform"


def test_owner_for_extracts_email():
    j = _job(ownership={"email": "ops@example.com"})
    assert owner_for(j).email == "ops@example.com"


def test_owner_for_extracts_slack():
    j = _job(ownership={"slack": "#ops"})
    assert owner_for(j).slack == "#ops"


def test_owner_for_extra_keys_captured():
    j = _job(ownership={"team": "data", "pagerduty": "svc123"})
    info = owner_for(j)
    assert info.extra == {"pagerduty": "svc123"}


# ---------------------------------------------------------------------------
# has_contact
# ---------------------------------------------------------------------------

def test_has_contact_true_when_email_set():
    assert OwnerInfo(email="a@b.com").has_contact() is True


def test_has_contact_true_when_slack_set():
    assert OwnerInfo(slack="#ch").has_contact() is True


def test_has_contact_false_when_only_team():
    assert OwnerInfo(team="infra").has_contact() is False


# ---------------------------------------------------------------------------
# jobs_owned_by_team
# ---------------------------------------------------------------------------

def test_jobs_owned_by_team_returns_matching():
    jobs = [
        _job("a", {"team": "platform"}),
        _job("b", {"team": "data"}),
        _job("c", {"team": "Platform"}),
    ]
    result = jobs_owned_by_team(jobs, "platform")
    assert [j.name for j in result] == ["a", "c"]


def test_jobs_owned_by_team_empty_when_no_match():
    jobs = [_job("a", {"team": "infra"})]
    assert jobs_owned_by_team(jobs, "data") == []


# ---------------------------------------------------------------------------
# jobs_without_owner
# ---------------------------------------------------------------------------

def test_jobs_without_owner_returns_unowned():
    jobs = [_job("a"), _FakeJob("b", None), _job("c", {"team": "ops"})]
    result = jobs_without_owner(jobs)
    assert {j.name for j in result} == {"a", "b"}


# ---------------------------------------------------------------------------
# all_teams
# ---------------------------------------------------------------------------

def test_all_teams_sorted_and_deduplicated():
    jobs = [
        _job("a", {"team": "zebra"}),
        _job("b", {"team": "alpha"}),
        _job("c", {"team": "zebra"}),
        _job("d"),
    ]
    assert all_teams(jobs) == ["alpha", "zebra"]


def test_all_teams_empty_when_no_teams():
    assert all_teams([_job("a"), _job("b")]) == []


# ---------------------------------------------------------------------------
# group_by_team
# ---------------------------------------------------------------------------

def test_group_by_team_partitions_correctly():
    a = _job("a", {"team": "ops"})
    b = _job("b", {"team": "dev"})
    c = _job("c")
    groups = group_by_team([a, b, c])
    assert groups["ops"] == [a]
    assert groups["dev"] == [b]
    assert groups[None] == [c]


def test_group_by_team_empty_input():
    assert group_by_team([]) == {}
