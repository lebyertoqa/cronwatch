"""Per-job cooldown enforcement: prevents a job from being re-queued
before a minimum interval has elapsed since its last completion."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from cronwatch.config import JobConfig


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class CooldownPolicy:
    """Maps job names to their minimum re-run interval in seconds."""

    default_seconds: int = 0
    per_job: Dict[str, int] = field(default_factory=dict)

    def seconds_for(self, job: JobConfig) -> int:
        """Return the cooldown duration (seconds) for *job*."""
        return self.per_job.get(job.name, self.default_seconds)


class CooldownTracker:
    """Tracks the last completion time of each job and enforces cooldowns."""

    def __init__(self, policy: CooldownPolicy) -> None:
        self._policy = policy
        self._last_completed: Dict[str, datetime] = {}

    def record_completion(self, job: JobConfig, at: Optional[datetime] = None) -> None:
        """Record that *job* completed at *at* (defaults to now)."""
        self._last_completed[job.name] = at if at is not None else _utcnow()

    def is_cooling_down(self, job: JobConfig, now: Optional[datetime] = None) -> bool:
        """Return True if *job* must not yet be re-queued."""
        last = self._last_completed.get(job.name)
        if last is None:
            return False
        seconds = self._policy.seconds_for(job)
        if seconds <= 0:
            return False
        effective_now = now if now is not None else _utcnow()
        return (effective_now - last) < timedelta(seconds=seconds)

    def next_allowed(self, job: JobConfig, now: Optional[datetime] = None) -> Optional[datetime]:
        """Return the earliest datetime at which *job* may next run, or None."""
        last = self._last_completed.get(job.name)
        if last is None:
            return None
        seconds = self._policy.seconds_for(job)
        if seconds <= 0:
            return None
        return last + timedelta(seconds=seconds)

    def reset(self, job: JobConfig) -> None:
        """Clear cooldown state for *job*."""
        self._last_completed.pop(job.name, None)
