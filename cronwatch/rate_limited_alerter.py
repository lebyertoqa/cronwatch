"""Decorator that wraps an Alerter with per-job rate limiting."""

from __future__ import annotations

import logging
from typing import Optional

from cronwatch.alerting import Alerter
from cronwatch.executor import ExecutionResult
from cronwatch.ratelimit import RateLimiter

log = logging.getLogger(__name__)


class RateLimitedAlerter(Alerter):
    """Wraps another :class:`Alerter` and suppresses alerts that exceed the
    configured rate limit for a given job.

    Args:
        inner: The underlying alerter that actually sends notifications.
        limiter: A :class:`RateLimiter` instance shared across the application.
    """

    def __init__(self, inner: Alerter, limiter: Optional[RateLimiter] = None) -> None:
        self._inner = inner
        self._limiter = limiter or RateLimiter()

    # ------------------------------------------------------------------
    # Alerter interface
    # ------------------------------------------------------------------

    def send(self, result: ExecutionResult) -> None:
        """Forward *result* to the inner alerter if the rate limit allows it."""
        job = result.job_name
        if not self._limiter.is_allowed(job):
            remaining_slots = self._limiter.remaining(job)
            log.warning(
                "Rate limit reached for job '%s'; alert suppressed "
                "(%d slot(s) remaining in window).",
                job,
                remaining_slots,
            )
            return

        self._limiter.record(job)
        log.debug("Forwarding alert for job '%s' (%d remaining).", job, self._limiter.remaining(job))
        self._inner.send(result)

    def reset(self, job_name: str) -> None:
        """Reset the rate-limit window for *job_name* (call on success)."""
        self._limiter.reset(job_name)


def build_rate_limited_alerter(
    inner: Alerter,
    window_seconds: float = 3600.0,
    max_alerts: int = 5,
) -> RateLimitedAlerter:
    """Convenience factory that creates a :class:`RateLimitedAlerter`.

    Args:
        inner: The underlying alerter.
        window_seconds: Sliding window length in seconds.
        max_alerts: Maximum alerts per job within the window.
    """
    limiter = RateLimiter(window_seconds=window_seconds, max_alerts=max_alerts)
    return RateLimitedAlerter(inner, limiter)
