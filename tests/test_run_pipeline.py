"""Tests for cronwatch.run_pipeline."""
from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.config import JobConfig, CronwatchConfig, AlertConfig
from cronwatch.executor import ExecutionResult
from cronwatch.history import HistoryStore
from cronwatch.job_runner import RunnerResult
from cronwatch.run_pipeline import RunPipeline


def _utc(**kw) -> datetime.datetime:
    return datetime.datetime(2024, 1, 1, 12, 0, 0, **kw).replace(
        tzinfo=datetime.timezone.utc
    )


def _job(name: str = "j1") -> JobConfig:
    return JobConfig(name=name, command="echo hi", schedule="* * * * *")


def _result(name: str = "j1", success: bool = True) -> ExecutionResult:
    return ExecutionResult(
        job_name=name,
        success=success,
        exit_code=0 if success else 1,
        stdout="",
        stderr="",
        duration=0.1,
        started_at=_utc(),
    )


@pytest.fixture()
def store(tmp_path: Path) -> HistoryStore:
    return HistoryStore(str(tmp_path / "history.json"))


def _make_pipeline(
    store: HistoryStore,
    job: JobConfig = None,
    runner_result: RunnerResult = None,
    is_due: bool = True,
    should_notify: bool = False,
    circuit_open: bool = False,
):
    job = job or _job()
    config = CronwatchConfig(
        jobs=[job],
        alert=AlertConfig(email_to=[], smtp_host=""),
    )
    scheduler = MagicMock()
    scheduler.is_due.return_value = is_due

    runner = MagicMock()
    runner.run.return_value = runner_result or RunnerResult(result=_result())

    notifier = MagicMock()
    notifier.should_notify.return_value = should_notify

    alerter = MagicMock()

    cb = MagicMock()
    cb.is_open.return_value = circuit_open

    pipeline = RunPipeline(
        config=config,
        scheduler=scheduler,
        runner=runner,
        history=store,
        notifier=notifier,
        alerter=alerter,
        circuit_breaker=cb,
    )
    return pipeline, alerter, notifier, cb


def test_job_not_due_produces_no_outcomes(store):
    pipeline, *_ = _make_pipeline(store, is_due=False)
    assert pipeline.tick() == []


def test_due_job_runs_and_records(store):
    pipeline, alerter, notifier, _ = _make_pipeline(store)
    outcomes = pipeline.tick()
    assert len(outcomes) == 1
    assert outcomes[0].ran
    assert outcomes[0].success


def test_failure_notifies_alerter(store):
    rr = RunnerResult(result=_result(success=False))
    pipeline, alerter, notifier, _ = _make_pipeline(
        store, runner_result=rr, should_notify=True
    )
    outcomes = pipeline.tick()
    alerter.send.assert_called_once()
    assert outcomes[0].notified


def test_success_no_notification_when_notifier_says_no(store):
    pipeline, alerter, *_ = _make_pipeline(store, should_notify=False)
    pipeline.tick()
    alerter.send.assert_not_called()


def test_circuit_open_skips_job(store):
    pipeline, alerter, _, cb = _make_pipeline(store, circuit_open=True)
    outcomes = pipeline.tick()
    assert outcomes[0].skipped
    assert outcomes[0].skip_reason == "circuit open"
    alerter.send.assert_not_called()


def test_locked_job_skipped(store):
    rr = RunnerResult(result=None, skipped=True, skip_reason="already locked")
    pipeline, alerter, *_ = _make_pipeline(store, runner_result=rr)
    outcomes = pipeline.tick()
    assert outcomes[0].skipped
    assert "already locked" in outcomes[0].skip_reason
    alerter.send.assert_not_called()
