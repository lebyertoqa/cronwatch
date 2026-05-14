"""Tests for cronwatch.pause_executor."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock

import pytest

from cronwatch.executor import ExecutionResult
from cronwatch.job_pause import PauseStore
from cronwatch.pause_executor import PauseAwareExecutor, PauseSkipResult, build_pause_aware_executor


def _utc(**kw) -> datetime:
    return datetime(2024, 1, 1, tzinfo=timezone.utc)


@dataclass
class _FakeJob:
    name: str
    command: str = "echo hello"


def _ok_result(name: str) -> ExecutionResult:
    return ExecutionResult(
        job_name=name,
        returncode=0,
        stdout="ok",
        stderr="",
        duration=0.1,
        started_at=_utc(),
    )


@pytest.fixture
def store(tmp_path: Path) -> PauseStore:
    return PauseStore(tmp_path / "pause.json")


@pytest.fixture
def inner():
    return MagicMock()


@pytest.fixture
def executor(inner, store: PauseStore) -> PauseAwareExecutor:
    return PauseAwareExecutor(inner=inner, store=store)


def test_unpaused_job_delegates_to_inner(executor, inner, store):
    job = _FakeJob(name="reports")
    inner.run.return_value = _ok_result("reports")
    result = executor.run(job)
    inner.run.assert_called_once_with(job)
    assert isinstance(result, ExecutionResult)


def test_paused_job_returns_skip_result(executor, inner, store):
    store.pause("backup")
    job = _FakeJob(name="backup")
    result = executor.run(job)
    inner.run.assert_not_called()
    assert isinstance(result, PauseSkipResult)
    assert result.skipped is True
    assert result.job_name == "backup"


def test_skip_result_includes_reason(executor, inner, store):
    store.pause("cleanup", reason="maintenance")
    job = _FakeJob(name="cleanup")
    result = executor.run(job)
    assert isinstance(result, PauseSkipResult)
    assert result.reason == "maintenance"


def test_skip_result_str_with_reason(store):
    r = PauseSkipResult(job_name="myjob", reason="scheduled downtime")
    assert "myjob" in str(r)
    assert "scheduled downtime" in str(r)


def test_skip_result_str_without_reason():
    r = PauseSkipResult(job_name="myjob", reason=None)
    assert "myjob" in str(r)


def test_resumed_job_runs_normally(executor, inner, store):
    store.pause("sync")
    store.resume("sync")
    job = _FakeJob(name="sync")
    inner.run.return_value = _ok_result("sync")
    result = executor.run(job)
    inner.run.assert_called_once_with(job)
    assert isinstance(result, ExecutionResult)


def test_build_pause_aware_executor_returns_instance(inner, store):
    ex = build_pause_aware_executor(inner=inner, store=store)
    assert isinstance(ex, PauseAwareExecutor)
