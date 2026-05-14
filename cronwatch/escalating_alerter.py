"""Alerter wrapper that annotates messages with the current escalation level."""
from __future__ import annotations

from cronwatch.alerting import Alerter
from cronwatch.executor import ExecutionResult
from cronwatch.job_escalation import EscalationPolicy, EscalationTracker

_DEFAULT_POLICY = EscalationPolicy(
    levels=[
        # avoid circular import — populated by build helper
    ],
    default_level="warning",
)


class EscalatingAlerter:
    """Wraps an :class:`Alerter` and prefixes the subject with the escalation level."""

    def __init__(self, inner: Alerter, tracker: EscalationTracker) -> None:
        self._inner = inner
        self._tracker = tracker

    def send(self, result: ExecutionResult) -> None:
        if result.success:
            self._tracker.record_success(result.job_name)
            return
        level = self._tracker.record_failure(result.job_name)
        annotated = _annotate(result, level)
        self._inner.send(annotated)

    def current_level(self, job_name: str) -> str | None:
        return self._tracker.current_level(job_name)


def _annotate(result: ExecutionResult, level: str) -> ExecutionResult:
    """Return a shallow copy of *result* with the level prepended to the job name
    so that downstream alerters surface it in subject lines."""
    # ExecutionResult is a dataclass; we rebuild it with a decorated job_name.
    from dataclasses import replace  # available in Python 3.7+
    decorated = f"[{level.upper()}] {result.job_name}"
    return replace(result, job_name=decorated)


def build_escalating_alerter(
    inner: Alerter,
    policy: EscalationPolicy | None = None,
) -> EscalatingAlerter:
    """Factory used by :mod:`cronwatch.__main__` to wire up the alerter chain."""
    if policy is None:
        from cronwatch.job_escalation import EscalationLevel
        policy = EscalationPolicy(
            levels=[
                EscalationLevel(name="warning", after_failures=1),
                EscalationLevel(name="critical", after_failures=5),
            ],
            default_level="warning",
        )
    tracker = EscalationTracker(policy)
    return EscalatingAlerter(inner, tracker)
