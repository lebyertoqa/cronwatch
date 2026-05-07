"""Tests for cronwatch.job_dispatcher."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List
from unittest.mock import MagicMock

import pytest

from cronwatch.config import JobConfig
from cronwatch.executor import ExecutionResult
from cronwatch.job_dispatcher import JobDispatcher
from cronwatch.job_queue import JobQueue


def _utc(**kw) -> datetime:
    return datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc).replace(**kw)


def _job(name: str, schedule: str = "* * * * *") -> JobConfig:
    return JobConfig(name=name, command=f"echo {name}", schedule=schedule)


def _ok_result(job: JobConfig) -> ExecutionResult:
    return ExecutionResult(
        job_name=job.name,
        success=True,
        exit_code=0,
        stdout="ok",
        stderr="",
        duration=0.1,
        started_at=datetime.now(tz=timezone.utc),
    )


NOW = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def queue() -> JobQueue:
    return JobQueue()


def _make_dispatcher(
    queue: JobQueue,
    runner=None,
    on_result=None,
) -> JobDispatcher:
    if runner is None:
        runner = _ok_result
    return JobDispatcher(queue=queue, runner=runner, on_result=on_result)


def test_tick_with_no_due_jobs_returns_empty(queue: JobQueue) -> None:
    dispatcher = _make_dispatcher(queue)
    queue.push(_job("a"), NOW + timedelta(minutes=5))
    results = dispatcher.tick(NOW)
    assert results == []


def test_tick_executes_due_job(queue: JobQueue) -> None:
    dispatcher = _make_dispatcher(queue)
    queue.push(_job("a"), NOW)
    results = dispatcher.tick(NOW)
    assert len(results) == 1
    assert results[0].job_name == "a"


def test_tick_reschedules_job_after_execution(queue: JobQueue) -> None:
    dispatcher = _make_dispatcher(queue)
    queue.push(_job("a"), NOW)
    dispatcher.tick(NOW)
    # Job should be back in the queue for the next minute
    assert len(queue) == 1
    top = queue.peek()
    assert top is not None
    assert top.next_run > NOW


def test_on_result_callback_called(queue: JobQueue) -> None:
    received: List[ExecutionResult] = []
    dispatcher = _make_dispatcher(queue, on_result=received.append)
    queue.push(_job("a"), NOW)
    dispatcher.tick(NOW)
    assert len(received) == 1
    assert received[0].job_name == "a"


def test_results_accumulate_across_ticks(queue: JobQueue) -> None:
    dispatcher = _make_dispatcher(queue)
    queue.push(_job("a"), NOW)
    dispatcher.tick(NOW)
    # Re-push manually for a second tick
    queue.push(_job("b"), NOW + timedelta(minutes=1))
    dispatcher.tick(NOW + timedelta(minutes=1))
    assert len(dispatcher.results) == 2


def test_seed_populates_queue(queue: JobQueue) -> None:
    dispatcher = _make_dispatcher(queue)
    jobs = [_job("x"), _job("y")]
    dispatcher.seed(jobs, after=NOW)
    assert len(queue) == 2


def test_multiple_due_jobs_all_executed(queue: JobQueue) -> None:
    dispatcher = _make_dispatcher(queue)
    for name in ("a", "b", "c"):
        queue.push(_job(name), NOW - timedelta(seconds=1))
    results = dispatcher.tick(NOW)
    assert len(results) == 3
    names = {r.job_name for r in results}
    assert names == {"a", "b", "c"}
