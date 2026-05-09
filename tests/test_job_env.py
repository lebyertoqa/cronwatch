"""Tests for cronwatch.job_env."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from cronwatch.job_env import env_for, merged_env, missing_required, redacted_env


def _job(env=None):
    job = MagicMock()
    job.env = env
    return job


# ---------------------------------------------------------------------------
# env_for
# ---------------------------------------------------------------------------

def test_env_for_returns_empty_when_none():
    assert env_for(_job(env=None)) == {}


def test_env_for_returns_empty_when_empty_dict():
    assert env_for(_job(env={})) == {}


def test_env_for_returns_correct_mapping():
    job = _job(env={"FOO": "bar", "BAZ": "qux"})
    assert env_for(job) == {"FOO": "bar", "BAZ": "qux"}


def test_env_for_returns_copy():
    original = {"KEY": "value"}
    job = _job(env=original)
    result = env_for(job)
    result["KEY"] = "mutated"
    assert original["KEY"] == "value"


# ---------------------------------------------------------------------------
# merged_env
# ---------------------------------------------------------------------------

def test_merged_env_overlays_job_vars():
    job = _job(env={"JOB_VAR": "from_job"})
    base = {"BASE_VAR": "base", "JOB_VAR": "from_base"}
    result = merged_env(job, base=base)
    assert result["JOB_VAR"] == "from_job"
    assert result["BASE_VAR"] == "base"


def test_merged_env_does_not_mutate_base():
    job = _job(env={"X": "1"})
    base = {"X": "0"}
    merged_env(job, base=base)
    assert base["X"] == "0"


def test_merged_env_uses_os_environ_by_default():
    job = _job(env={"CRONWATCH_TEST_KEY": "hello"})
    result = merged_env(job)
    assert result["CRONWATCH_TEST_KEY"] == "hello"
    # Should also contain real env vars
    assert "PATH" in result or len(result) > 1


def test_merged_env_no_job_env_equals_base():
    job = _job(env=None)
    base = {"A": "1", "B": "2"}
    assert merged_env(job, base=base) == base


# ---------------------------------------------------------------------------
# missing_required
# ---------------------------------------------------------------------------

def test_missing_required_all_present():
    job = _job(env={"A": "1", "B": "2"})
    assert missing_required(job, ["A", "B"]) == []


def test_missing_required_some_absent():
    job = _job(env={"A": "1"})
    missing = missing_required(job, ["A", "B", "C"])
    assert missing == ["B", "C"]


def test_missing_required_empty_required_list():
    job = _job(env={"A": "1"})
    assert missing_required(job, []) == []


# ---------------------------------------------------------------------------
# redacted_env
# ---------------------------------------------------------------------------

def test_redacted_env_hides_secret_keys():
    job = _job(env={"API_KEY": "secret", "HOST": "localhost"})
    result = redacted_env(job, secret_keys=["API_KEY"])
    assert result["API_KEY"] == "***"
    assert result["HOST"] == "localhost"


def test_redacted_env_no_secrets_returns_plain():
    job = _job(env={"FOO": "bar"})
    assert redacted_env(job) == {"FOO": "bar"}


def test_redacted_env_unknown_secret_key_ignored():
    job = _job(env={"FOO": "bar"})
    result = redacted_env(job, secret_keys=["MISSING_KEY"])
    assert result == {"FOO": "bar"}
