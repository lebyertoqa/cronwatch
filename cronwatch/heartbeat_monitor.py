"""Monitors job heartbeats and emits alerts when jobs go silent.

The HeartbeatMonitor is ticked periodically; it checks every tracked job
against its TTL and fires an alert (via Alerter) when the heartbeat has
expired and no alert has already been sent for that expiry window.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from cronwatch.alerting import Alerter
from cronwatch.job_heartbeat import HeartbeatStore


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class HeartbeatViolation:
    job_name: str
    last_success: datetime
    age_seconds: float
    ttl_seconds: float

    def __str__(self) -> str:
        return (
            f"{self.job_name}: heartbeat expired "
            f"(age={self.age_seconds:.0f}s, ttl={self.ttl_seconds:.0f}s)"
        )


class HeartbeatMonitor:
    """Checks heartbeats and alerts on stale jobs."""

    def __init__(
        self,
        store: HeartbeatStore,
        alerter: Alerter,
        ttl_seconds: float = 3600.0,
        per_job_ttl: Optional[Dict[str, float]] = None,
    ) -> None:
        self._store = store
        self._alerter = alerter
        self._default_ttl = ttl_seconds
        self._per_job_ttl: Dict[str, float] = per_job_ttl or {}
        self._alerted: Dict[str, datetime] = {}

    def _ttl_for(self, job_name: str) -> float:
        return self._per_job_ttl.get(job_name, self._default_ttl)

    def tick(self, now: Optional[datetime] = None) -> List[HeartbeatViolation]:
        now = now or _utcnow()
        violations: List[HeartbeatViolation] = []
        for name, entry in self._store.all().items():
            ttl = self._ttl_for(name)
            if not entry.is_alive(ttl, now):
                last_alert = self._alerted.get(name)
                if last_alert is None or (now - last_alert).total_seconds() > ttl:
                    age = entry.age_seconds(now)
                    v = HeartbeatViolation(
                        job_name=name,
                        last_success=entry.last_success,
                        age_seconds=age,
                        ttl_seconds=ttl,
                    )
                    violations.append(v)
                    self._alerter.send(
                        subject=f"[cronwatch] Heartbeat expired: {name}",
                        body=str(v),
                    )
                    self._alerted[name] = now
        return violations

    def reset(self, job_name: str) -> None:
        """Clear the alerted state for a job (e.g. after it recovers)."""
        self._alerted.pop(job_name, None)
