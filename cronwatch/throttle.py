"""Rate-limiting / back-off logic for alert delivery.

Prevents alert storms by enforcing a minimum interval between
consecutive alerts for the same job, with optional exponential
back-off when a job keeps failing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class _JobThrottleState:
    last_alert_at: float = 0.0
    consecutive_alerts: int = 0


@dataclass
class ThrottlePolicy:
    """Configuration for the throttle behaviour."""

    base_interval_seconds: int = 300          # 5 minutes
    backoff_multiplier: float = 2.0
    max_interval_seconds: int = 3600          # 1 hour
    reset_on_success: bool = True

    def interval_for(self, consecutive: int) -> float:
        """Return the required quiet period after *consecutive* alerts."""
        interval = self.base_interval_seconds * (
            self.backoff_multiplier ** max(consecutive - 1, 0)
        )
        return min(interval, self.max_interval_seconds)


class AlertThrottle:
    """Decides whether an alert should be sent, honouring back-off rules."""

    def __init__(self, policy: Optional[ThrottlePolicy] = None) -> None:
        self._policy = policy or ThrottlePolicy()
        self._states: Dict[str, _JobThrottleState] = {}

    def _state(self, job_name: str) -> _JobThrottleState:
        if job_name not in self._states:
            self._states[job_name] = _JobThrottleState()
        return self._states[job_name]

    def allow(self, job_name: str, success: bool) -> bool:
        """Return *True* if an alert may be sent right now.

        Side-effect: updates internal state regardless of the return value.
        """
        state = self._state(job_name)

        if success:
            if self._policy.reset_on_success:
                self._states.pop(job_name, None)
            return False  # successes never trigger an alert via throttle

        now = time.monotonic()
        required = self._policy.interval_for(state.consecutive_alerts)
        elapsed = now - state.last_alert_at

        if elapsed >= required:
            state.last_alert_at = now
            state.consecutive_alerts += 1
            return True

        return False

    def reset(self, job_name: str) -> None:
        """Manually clear throttle state for *job_name*."""
        self._states.pop(job_name, None)
