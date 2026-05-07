"""Tests for cronwatch.job_selector.select_jobs."""
from __future__ import annotations

from typing import List, Optional

import pytest

from cronwatch.config import AlertConfig, CronwatchConfig, JobConfig
from cronwatch.job_selector import select_jobs


def _job(
    name: str,
    tags: Optional[List[str]] = None,
    enabled: bool = True,
) -> JobConfig:
    return JobConfig(
        name=name,
        command=f"echo {name}",
        schedule="* * * * *",
        tags=tags or [],
        enabled=enabled,
    )


def _config(jobs: List[JobConfig]) -> CronwatchConfig:
    return CronwatchConfig(
        jobs=jobs,
        alert=AlertConfig(email=[]),
    )


def test_select_all_enabled_by_default():
    cfg = _config([_job("a"), _job("b", enabled=False)])
    result = select_jobs(cfg)
    assert [j.name for j in result] == ["a"]


def test_include_disabled_flag():
    cfg = _config([_job("a"), _job("b", enabled=False)])
    result = select_jobs(cfg, include_disabled=True)
    assert {j.name for j in result} == {"a", "b"}


def test_filter_by_tag():
    cfg = _config([
        _job("db", tags=["critical"]),
        _job("report", tags=["nightly"]),
    ])
    result = select_jobs(cfg, tags=["critical"])
    assert [j.name for j in result] == ["db"]


def test_filter_by_name_pattern():
    cfg = _config([_job("backup-daily"), _job("backup-weekly"), _job("restore")])
    result = select_jobs(cfg, name_pattern="backup-*")
    assert [j.name for j in result] == ["backup-daily", "backup-weekly"]


def test_no_criteria_returns_all_enabled():
    cfg = _config([_job("x"), _job("y")])
    result = select_jobs(cfg)
    assert len(result) == 2


def test_empty_config_returns_empty():
    cfg = _config([])
    assert select_jobs(cfg) == []
