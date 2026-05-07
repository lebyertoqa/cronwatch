"""Integration-style tests for RunPipeline using real sub-components."""
from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from cronwatch.config import JobConfig, CronwatchConfig, AlertConfig
from cronwatch.executor import ExecutionResult
from cronwatch.history import HistoryStore
from cronwatch.job_runner import build_job_runner
from cronwatch.notifier import Notifier
from cronwatch.run_pipeline import RunPipeline
from cronwatch.scheduler import Scheduler
from cronwatch.alerting import Alerter


def _utc() -> datetime.datetime:
    return datetime.datetime(2024, 6, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)


def _job(name: str, cmd: str) -> JobConfig:
    return JobConfig(name=name, command=cmd, schedule="* * * * *")


@pytest.fixture()
def tmp_dirs(tmp_path: Path):
    return {
        "locks": str(tmp_path / "locks"),
        "history": str(tmp_path / "history.json"),
        "notifier": str(tmp_path / "notifier.json"),
    }


def _build_pipeline(jobs, tmp_dirs, alert_interval=0):
    (Path(tmp_dirs["locks"])).mkdir(parents=True, exist_ok=True)
    config = CronwatchConfig(
        jobs=jobs,
        alert=AlertConfig(email_to=["a@b.com"], smtp_host="localhost"),
    )
    scheduler = Scheduler(config)
    runner = build_job_runner(lock_dir=tmp_dirs["locks"])
    history = HistoryStore(tmp_dirs["history"])
    notifier = Notifier(state_path=tmp_dirs["notifier"], interval_seconds=alert_interval)
    alerter = Alerter.__new__(Alerter)
    alerter._backends = []
    return RunPipeline(
        config=config,
        scheduler=scheduler,
        runner=runner,
        history=history,
        notifier=notifier,
        alerter=alerter,
    )


def test_successful_job_recorded_in_history(tmp_dirs):
    job = _job("ok-job", "echo success")
    pipeline = _build_pipeline([job], tmp_dirs)
    with patch("cronwatch.scheduler.is_due", return_value=True):
        pipeline.tick()
    store = HistoryStore(tmp_dirs["history"])
    entries = store.get("ok-job", limit=5)
    assert len(entries) == 1
    assert entries[0].success


def test_failed_job_recorded_in_history(tmp_dirs):
    job = _job("bad-job", "exit 1")
    pipeline = _build_pipeline([job], tmp_dirs)
    with patch("cronwatch.scheduler.is_due", return_value=True):
        pipeline.tick()
    store = HistoryStore(tmp_dirs["history"])
    entries = store.get("bad-job", limit=5)
    assert len(entries) == 1
    assert not entries[0].success
