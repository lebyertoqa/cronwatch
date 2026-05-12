"""Tests for cronwatch.conditional_executor."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronwatch.conditional_executor import (
    ConditionalExecutor,
    ConditionalResult,
    build_conditional_executor,
)
from cronwatch.executor import ExecutionResult


def _job(name: str = "myjob", conditions=None):
    job = MagicMock()
    job.name = name
    job.conditions = conditions
    return job


def _ok_result(name: str = "myjob") -> ExecutionResult:
    r = MagicMock(spec=ExecutionResult)
    r.success = True
    r.job_name = name
    return r


def _fail_result(name: str = "myjob") -> ExecutionResult:
    r = MagicMock(spec=ExecutionResult)
    r.success = False
    r.job_name = name
    return r


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_inner(result):
    inner = MagicMock()
    inner.run.return_value = result
    return inner


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_no_conditions_runs_job():
    inner = _make_inner(_ok_result())
    executor = ConditionalExecutor(inner)
    cr = executor.run(_job(conditions=[]))
    assert cr.skipped is False
    inner.run.assert_called_once()


def test_passing_condition_runs_job():
    inner = _make_inner(_ok_result())
    executor = ConditionalExecutor(inner)
    cr = executor.run(_job(conditions=["true"]))
    assert cr.skipped is False
    assert cr.execution_result is not None


def test_failing_condition_skips_job():
    inner = _make_inner(_ok_result())
    executor = ConditionalExecutor(inner)
    cr = executor.run(_job(conditions=["false"]))
    assert cr.skipped is True
    inner.run.assert_not_called()


def test_skip_reason_contains_command():
    inner = _make_inner(_ok_result())
    executor = ConditionalExecutor(inner)
    cr = executor.run(_job(conditions=["false"]))
    assert "false" in (cr.skip_reason or "")


def test_skipped_result_not_succeeded():
    inner = _make_inner(_ok_result())
    executor = ConditionalExecutor(inner)
    cr = executor.run(_job(conditions=["false"]))
    assert cr.succeeded is False


def test_successful_execution_is_succeeded():
    inner = _make_inner(_ok_result())
    executor = ConditionalExecutor(inner)
    cr = executor.run(_job(conditions=["true"]))
    assert cr.succeeded is True


def test_failed_execution_not_succeeded():
    inner = _make_inner(_fail_result())
    executor = ConditionalExecutor(inner)
    cr = executor.run(_job(conditions=["true"]))
    assert cr.succeeded is False


def test_condition_check_attached_to_result():
    inner = _make_inner(_ok_result())
    executor = ConditionalExecutor(inner)
    cr = executor.run(_job(conditions=["true"]))
    assert cr.condition_check is not None


def test_job_name_stored():
    inner = _make_inner(_ok_result("backup"))
    executor = ConditionalExecutor(inner)
    cr = executor.run(_job(name="backup", conditions=[]))
    assert cr.job_name == "backup"


def test_build_conditional_executor_returns_instance():
    inner = _make_inner(_ok_result())
    executor = build_conditional_executor(inner, condition_timeout=5)
    assert isinstance(executor, ConditionalExecutor)
