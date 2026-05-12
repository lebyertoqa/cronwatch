"""Tests for cronwatch.job_conditions."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.job_conditions import (
    ConditionCheck,
    ConditionResult,
    check_conditions,
    conditions_for,
    evaluate_condition,
)


def _job(name: str = "myjob", conditions=None):
    job = MagicMock()
    job.name = name
    job.conditions = conditions
    return job


# ---------------------------------------------------------------------------
# conditions_for
# ---------------------------------------------------------------------------

def test_conditions_for_returns_empty_when_none():
    assert conditions_for(_job(conditions=None)) == []


def test_conditions_for_returns_empty_when_empty_list():
    assert conditions_for(_job(conditions=[])) == []


def test_conditions_for_returns_list():
    job = _job(conditions=["true", "test -f /etc/hosts"])
    assert conditions_for(job) == ["true", "test -f /etc/hosts"]


def test_conditions_for_returns_copy():
    original = ["true"]
    job = _job(conditions=original)
    result = conditions_for(job)
    result.append("extra")
    assert conditions_for(job) == ["true"]


# ---------------------------------------------------------------------------
# evaluate_condition
# ---------------------------------------------------------------------------

def test_evaluate_condition_passing_command():
    result = evaluate_condition("true")
    assert result.passed is True
    assert result.returncode == 0


def test_evaluate_condition_failing_command():
    result = evaluate_condition("false")
    assert result.passed is False
    assert result.returncode != 0


def test_evaluate_condition_timeout_returns_failure():
    # Use a very short timeout with a command that sleeps.
    result = evaluate_condition("sleep 10", timeout=0)
    assert result.passed is False
    assert result.returncode == -1
    assert "timed out" in result.stderr


def test_evaluate_condition_stores_command():
    cmd = "true"
    result = evaluate_condition(cmd)
    assert result.command == cmd


# ---------------------------------------------------------------------------
# check_conditions
# ---------------------------------------------------------------------------

def test_check_all_conditions_pass():
    job = _job(conditions=["true", "true"])
    check = check_conditions(job)
    assert check.all_passed is True
    assert len(check.results) == 2


def test_check_fails_fast_on_first_failure():
    job = _job(conditions=["false", "true"])
    check = check_conditions(job)
    assert check.all_passed is False
    # Should stop after the first failure.
    assert len(check.results) == 1


def test_check_no_conditions_passes():
    job = _job(conditions=[])
    check = check_conditions(job)
    assert check.all_passed is True
    assert check.results == []


def test_check_first_failure_returns_failed_result():
    job = _job(conditions=["false"])
    check = check_conditions(job)
    assert check.first_failure is not None
    assert check.first_failure.passed is False


def test_check_first_failure_none_when_all_pass():
    job = _job(conditions=["true"])
    check = check_conditions(job)
    assert check.first_failure is None


def test_check_stores_job_name():
    job = _job(name="backup", conditions=["true"])
    check = check_conditions(job)
    assert check.job_name == "backup"
