"""Dispatcher: pulls due jobs from a JobQueue and executes them."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, List, Optional

from cronwatch.config import JobConfig
from cronwatch.executor import ExecutionResult
from cronwatch.job_queue import JobQueue, QueuedJob
from cronwatch.scheduler import next_run

RunnerFn = Callable[[JobConfig], ExecutionResult]


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class JobDispatcher:
    """Dequeues due jobs, runs them, and re-schedules them."""

    def __init__(
        self,
        queue: JobQueue,
        runner: RunnerFn,
        on_result: Optional[Callable[[ExecutionResult], None]] = None,
    ) -> None:
        self._queue = queue
        self._runner = runner
        self._on_result = on_result
        self._results: List[ExecutionResult] = []

    def tick(self, now: Optional[datetime] = None) -> List[ExecutionResult]:
        """Execute all jobs that are due by *now* and re-queue them.

        Returns the list of results produced in this tick.
        """
        if now is None:
            now = _utcnow()

        due: List[QueuedJob] = self._queue.drain_due(now)
        tick_results: List[ExecutionResult] = []

        for queued in due:
            result = self._runner(queued.job)
            tick_results.append(result)
            self._results.append(result)

            if self._on_result is not None:
                self._on_result(result)

            # Re-schedule for next occurrence
            nxt = next_run(queued.job, after=now)
            self._queue.push(queued.job, nxt)

        return tick_results

    @property
    def results(self) -> List[ExecutionResult]:
        """All results collected since this dispatcher was created."""
        return list(self._results)

    def seed(self, jobs: List[JobConfig], after: Optional[datetime] = None) -> None:
        """Populate the queue with an initial set of jobs."""
        if after is None:
            after = _utcnow()
        for job in jobs:
            nxt = next_run(job, after=after)
            self._queue.push(job, nxt)
