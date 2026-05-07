"""Tests for cronwatch.job_queue."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from cronwatch.config import JobConfig
from cronwatch.job_queue import JobQueue, QueuedJob


def _utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _job(name: str) -> JobConfig:
    return JobConfig(name=name, command=f"echo {name}", schedule="* * * * *")


@pytest.fixture
def queue() -> JobQueue:
    return JobQueue()


NOW = _utc(2024, 6, 1, 12, 0)


def test_empty_queue_peek_returns_none(queue: JobQueue) -> None:
    assert queue.peek() is None


def test_empty_queue_pop_due_returns_none(queue: JobQueue) -> None:
    assert queue.pop_due(NOW) is None


def test_push_increases_length(queue: JobQueue) -> None:
    queue.push(_job("a"), NOW)
    assert len(queue) == 1


def test_bool_false_when_empty(queue: JobQueue) -> None:
    assert not queue


def test_bool_true_when_non_empty(queue: JobQueue) -> None:
    queue.push(_job("a"), NOW)
    assert queue


def test_peek_returns_earliest_job(queue: JobQueue) -> None:
    later = NOW + timedelta(minutes=5)
    queue.push(_job("b"), later)
    queue.push(_job("a"), NOW)
    top = queue.peek()
    assert top is not None
    assert top.job.name == "a"
    assert len(queue) == 2  # peek does not remove


def test_pop_due_returns_job_when_due(queue: JobQueue) -> None:
    queue.push(_job("a"), NOW)
    result = queue.pop_due(NOW)
    assert result is not None
    assert result.job.name == "a"
    assert len(queue) == 0


def test_pop_due_returns_none_when_not_yet_due(queue: JobQueue) -> None:
    future = NOW + timedelta(minutes=1)
    queue.push(_job("a"), future)
    result = queue.pop_due(NOW)
    assert result is None
    assert len(queue) == 1


def test_drain_due_returns_all_due_jobs(queue: JobQueue) -> None:
    queue.push(_job("a"), NOW - timedelta(seconds=10))
    queue.push(_job("b"), NOW)
    queue.push(_job("c"), NOW + timedelta(minutes=1))
    due = queue.drain_due(NOW)
    names = {item.job.name for item in due}
    assert names == {"a", "b"}
    assert len(queue) == 1


def test_drain_due_empty_when_none_ready(queue: JobQueue) -> None:
    queue.push(_job("a"), NOW + timedelta(minutes=1))
    assert queue.drain_due(NOW) == []


def test_jobs_ordered_by_next_run(queue: JobQueue) -> None:
    times = [NOW + timedelta(minutes=i) for i in (3, 1, 2)]
    names = ["c", "a", "b"]
    for name, t in zip(names, times):
        queue.push(_job(name), t)
    popped = []
    while queue:
        item = queue.pop_due(NOW + timedelta(hours=1))
        if item:
            popped.append(item.job.name)
    assert popped == ["a", "b", "c"]


def test_queued_job_str_contains_name() -> None:
    j = _job("myjob")
    qj = QueuedJob(next_run=NOW, job=j)
    assert "myjob" in str(qj)
