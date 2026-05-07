"""Priority queue for scheduling and dispatching cron jobs."""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from cronwatch.config import JobConfig


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass(order=True)
class QueuedJob:
    """A job waiting to be executed, ordered by next_run time."""
    next_run: datetime
    job: JobConfig = field(compare=False)

    def __str__(self) -> str:
        return f"QueuedJob({self.job.name!r}, next_run={self.next_run.isoformat()})"


class JobQueue:
    """Min-heap priority queue that returns jobs whose next_run is due."""

    def __init__(self) -> None:
        self._heap: List[QueuedJob] = []

    def push(self, job: JobConfig, next_run: datetime) -> None:
        """Add or re-schedule a job."""
        heapq.heappush(self._heap, QueuedJob(next_run=next_run, job=job))

    def peek(self) -> Optional[QueuedJob]:
        """Return the next job without removing it, or None if empty."""
        return self._heap[0] if self._heap else None

    def pop_due(self, now: Optional[datetime] = None) -> Optional[QueuedJob]:
        """Remove and return the earliest job if its next_run <= now."""
        if now is None:
            now = _utcnow()
        if self._heap and self._heap[0].next_run <= now:
            return heapq.heappop(self._heap)
        return None

    def drain_due(self, now: Optional[datetime] = None) -> List[QueuedJob]:
        """Remove and return ALL jobs that are due by *now*."""
        if now is None:
            now = _utcnow()
        due: List[QueuedJob] = []
        while True:
            item = self.pop_due(now)
            if item is None:
                break
            due.append(item)
        return due

    def __len__(self) -> int:
        return len(self._heap)

    def __bool__(self) -> bool:
        return bool(self._heap)
