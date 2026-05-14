"""Escalation policy: raise alert severity after repeated failures."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class EscalationLevel:
    name: str          # e.g. "warning", "critical"
    after_failures: int  # escalate once this many consecutive failures reached


@dataclass
class EscalationPolicy:
    levels: list[EscalationLevel] = field(default_factory=list)
    default_level: str = "warning"

    def level_for(self, consecutive_failures: int) -> str:
        """Return the highest escalation level reached for *consecutive_failures*."""
        current = self.default_level
        for lvl in sorted(self.levels, key=lambda l: l.after_failures):
            if consecutive_failures >= lvl.after_failures:
                current = lvl.name
        return current


@dataclass
class _EscalationState:
    consecutive_failures: int = 0
    last_level: Optional[str] = None


class EscalationTracker:
    """Tracks consecutive failures per job and determines alert escalation level."""

    def __init__(self, policy: EscalationPolicy) -> None:
        self._policy = policy
        self._states: Dict[str, _EscalationState] = {}

    def _get(self, job_name: str) -> _EscalationState:
        if job_name not in self._states:
            self._states[job_name] = _EscalationState()
        return self._states[job_name]

    def record_failure(self, job_name: str) -> str:
        """Record a failure and return the current escalation level."""
        state = self._get(job_name)
        state.consecutive_failures += 1
        level = self._policy.level_for(state.consecutive_failures)
        state.last_level = level
        return level

    def record_success(self, job_name: str) -> None:
        """Reset consecutive failure count on success."""
        state = self._get(job_name)
        state.consecutive_failures = 0
        state.last_level = None

    def consecutive_failures(self, job_name: str) -> int:
        return self._get(job_name).consecutive_failures

    def current_level(self, job_name: str) -> Optional[str]:
        return self._get(job_name).last_level

    def escalated(self, job_name: str) -> bool:
        """True when the job has moved beyond the default level."""
        lvl = self.current_level(job_name)
        return lvl is not None and lvl != self._policy.default_level
