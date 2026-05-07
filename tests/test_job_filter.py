"""Tests for cronwatch.job_filter and cronwatch.job_selector."""
from __future__ import annotations

from typing import List, Optional

import pytest

from cronwatch.config import JobConfig
from cronwatch.job_filter import JobFilter, apply_filter


def _job(
    name: str,
    tags: Optional[List[str]] = None,
    enabled: bool = True,
) -> JobConfig:
    """Create a minimal JobConfig for testing."""
    return JobConfig(
        name=name,
        command=f"echo {name}",
        schedule="* * * * *",
        tags=tags or [],
        enabled=enabled,
    )


# ---------------------------------------------------------------------------
# JobFilter.matches
# ---------------------------------------------------------------------------

def test_default_filter_matches_enabled_job():
    jf = JobFilter()
    assert jf.matches(_job("backup")) is True


def test_default_filter_excludes_disabled_job():
    jf = JobFilter(enabled_only=True)
    assert jf.matches(_job("backup", enabled=False)) is False


def test_include_disabled_flag():
    jf = JobFilter(enabled_only=False)
    assert jf.matches(_job("backup", enabled=False)) is True


def test_name_pattern_exact_match():
    jf = JobFilter(name_pattern="backup")
    assert jf.matches(_job("backup")) is True


def test_name_pattern_glob():
    jf = JobFilter(name_pattern="back*")
    assert jf.matches(_job("backup-daily")) is True
    assert jf.matches(_job("restore")) is False


def test_tag_filter_single_match():
    jf = JobFilter(tags=["critical"])
    assert jf.matches(_job("db", tags=["critical", "nightly"])) is True


def test_tag_filter_no_match():
    jf = JobFilter(tags=["critical"])
    assert jf.matches(_job("db", tags=["nightly"])) is False


def test_tag_filter_any_tag_sufficient():
    jf = JobFilter(tags=["critical", "fast"])
    assert jf.matches(_job("db", tags=["fast"])) is True


def test_combined_tag_and_pattern():
    jf = JobFilter(tags=["critical"], name_pattern="db*")
    assert jf.matches(_job("db-backup", tags=["critical"])) is True
    assert jf.matches(_job("db-backup", tags=["nightly"])) is False
    assert jf.matches(_job("restore", tags=["critical"])) is False


# ---------------------------------------------------------------------------
# apply_filter
# ---------------------------------------------------------------------------

def test_apply_filter_returns_matching_subset():
    jobs = [
        _job("backup", tags=["critical"]),
        _job("cleanup", tags=["nightly"]),
        _job("report", tags=["critical"]),
    ]
    jf = JobFilter(tags=["critical"])
    result = apply_filter(jobs, jf)
    assert [j.name for j in result] == ["backup", "report"]


def test_apply_filter_empty_list():
    assert apply_filter([], JobFilter()) == []


def test_apply_filter_all_excluded():
    jobs = [_job("backup", enabled=False)]
    assert apply_filter(jobs, JobFilter(enabled_only=True)) == []
