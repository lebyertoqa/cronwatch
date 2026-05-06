"""Per-job alert rate limiting with a sliding window counter."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict


@dataclass
class _WindowState:
    """Sliding window of alert timestamps for a single job."""
    timestamps: Deque[float] = field(default_factory=deque)

    def record(self, ts: float) -> None:
        self.timestamps.append(ts)

    def evict_before(self, cutoff: float) -> None:
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()

    def count(self) -> int:
        return len(self.timestamps)


class RateLimiter:
    """Allows at most *max_alerts* alerts per *window_seconds* for each job.

    Args:
        window_seconds: Length of the sliding window in seconds.
        max_alerts: Maximum number of alerts permitted within the window.
    """

    def __init__(self, window_seconds: float = 3600.0, max_alerts: int = 5) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if max_alerts < 1:
            raise ValueError("max_alerts must be at least 1")
        self._window = window_seconds
        self._max = max_alerts
        self._states: Dict[str, _WindowState] = {}

    def _state(self, job_name: str) -> _WindowState:
        if job_name not in self._states:
            self._states[job_name] = _WindowState()
        return self._states[job_name]

    def is_allowed(self, job_name: str, *, _now: float | None = None) -> bool:
        """Return True if an alert for *job_name* is within the rate limit."""
        now = _now if _now is not None else time.monotonic()
        state = self._state(job_name)
        state.evict_before(now - self._window)
        return state.count() < self._max

    def record(self, job_name: str, *, _now: float | None = None) -> None:
        """Record that an alert was sent for *job_name*."""
        now = _now if _now is not None else time.monotonic()
        state = self._state(job_name)
        state.evict_before(now - self._window)
        state.record(now)

    def remaining(self, job_name: str, *, _now: float | None = None) -> int:
        """Return how many more alerts are allowed for *job_name* in the current window."""
        now = _now if _now is not None else time.monotonic()
        state = self._state(job_name)
        state.evict_before(now - self._window)
        return max(0, self._max - state.count())

    def reset(self, job_name: str) -> None:
        """Clear the window state for *job_name* (e.g. after a successful run)."""
        self._states.pop(job_name, None)
