"""Notification rate-limiting and deduplication for cronwatch alerts."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from cronwatch.executor import ExecutionResult


@dataclass
class NotifierState:
    """Tracks per-job notification state."""
    last_notified_at: float = 0.0
    consecutive_failures: int = 0
    last_exit_code: Optional[int] = None


class Notifier:
    """Decides whether an alert should be sent based on rate-limiting rules.

    Args:
        min_interval_seconds: Minimum seconds between alerts for the same job.
        notify_on_recovery: If True, send an alert when a job recovers after failure.
    """

    def __init__(
        self,
        min_interval_seconds: int = 3600,
        notify_on_recovery: bool = True,
    ) -> None:
        self.min_interval_seconds = min_interval_seconds
        self.notify_on_recovery = notify_on_recovery
        self._states: Dict[str, NotifierState] = {}

    def _get_state(self, job_name: str) -> NotifierState:
        if job_name not in self._states:
            self._states[job_name] = NotifierState()
        return self._states[job_name]

    def should_notify(self, result: ExecutionResult) -> bool:
        """Return True if an alert should be sent for this result."""
        state = self._get_state(result.job_name)
        now = time.monotonic()

        if result.success:
            was_failing = (state.last_exit_code is not None and state.last_exit_code != 0)
            state.consecutive_failures = 0
            state.last_exit_code = 0
            if was_failing and self.notify_on_recovery:
                state.last_notified_at = now
                return True
            return False

        # Job failed
        state.consecutive_failures += 1
        state.last_exit_code = result.exit_code

        elapsed = now - state.last_notified_at
        if elapsed >= self.min_interval_seconds:
            state.last_notified_at = now
            return True

        return False

    def reset(self, job_name: str) -> None:
        """Reset state for a specific job (e.g. after config reload)."""
        self._states.pop(job_name, None)

    def consecutive_failures(self, job_name: str) -> int:
        """Return the current consecutive failure count for a job."""
        return self._get_state(job_name).consecutive_failures
