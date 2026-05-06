"""Circuit breaker that disables a cron job after repeated consecutive failures."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class _BreakerState:
    consecutive_failures: int = 0
    open_since: Optional[datetime] = None

    def is_open(self) -> bool:
        return self.open_since is not None


@dataclass
class CircuitBreaker:
    """Tracks consecutive failures per job and opens after *threshold* failures.

    Once open the breaker stays open until :py:meth:`reset` is called (or the
    job succeeds and the breaker is in half-open mode after *recovery_window*
    seconds).
    """

    threshold: int = 3
    recovery_window: int = 300  # seconds before allowing one retry
    _state: Dict[str, _BreakerState] = field(default_factory=dict, repr=False)

    def _get(self, job_name: str) -> _BreakerState:
        if job_name not in self._state:
            self._state[job_name] = _BreakerState()
        return self._state[job_name]

    def record_failure(self, job_name: str) -> None:
        """Record a failure; open the breaker if threshold is reached."""
        state = self._get(job_name)
        state.consecutive_failures += 1
        if state.consecutive_failures >= self.threshold and not state.is_open():
            state.open_since = _utcnow()

    def record_success(self, job_name: str) -> None:
        """Reset consecutive failure count and close the breaker."""
        state = self._get(job_name)
        state.consecutive_failures = 0
        state.open_since = None

    def is_open(self, job_name: str) -> bool:
        """Return True when the job should be suppressed / skipped."""
        state = self._get(job_name)
        if not state.is_open():
            return False
        elapsed = (_utcnow() - state.open_since).total_seconds()
        # Allow a single retry after recovery_window seconds (half-open)
        if elapsed >= self.recovery_window:
            return False
        return True

    def reset(self, job_name: str) -> None:
        """Manually close the breaker for *job_name*."""
        self._state.pop(job_name, None)

    def consecutive_failures(self, job_name: str) -> int:
        return self._get(job_name).consecutive_failures
