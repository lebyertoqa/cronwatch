"""Alert on deadline violations detected by :class:`DeadlineChecker`."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from cronwatch.alerting import Alerter
from cronwatch.job_deadline import DeadlineChecker, DeadlineViolation


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DeadlineAlerter:
    """Wraps a :class:`DeadlineChecker` and sends alerts for new violations.

    Each violation is alerted at most once per calendar day (keyed by job
    name + date string) to avoid flooding on repeated checks.
    """

    checker: DeadlineChecker
    alerter: Alerter
    _alerted: set = field(default_factory=set, init=False)

    def tick(self, now: Optional[datetime] = None) -> List[DeadlineViolation]:
        """Check for violations and send alerts for any that are new.

        Returns the list of *new* violations that triggered an alert.
        """
        now = now or _utcnow()
        violations = self.checker.check(now=now)
        new_violations: List[DeadlineViolation] = []
        for v in violations:
            key = (v.job_name, now.date().isoformat())
            if key in self._alerted:
                continue
            self._alerted.add(key)
            new_violations.append(v)
            self._send_alert(v)
        return new_violations

    def _send_alert(self, violation: DeadlineViolation) -> None:
        dl = violation.deadline.strftime("%H:%M UTC")
        subject = f"[cronwatch] Deadline missed: {violation.job_name}"
        body = (
            f"Job '{violation.job_name}' did not run before its deadline of {dl}.\n"
            f"Checked at: {violation.checked_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        # Alerter.send signature: send(subject, body)
        self.alerter.send(subject, body)

    def reset_daily(self) -> None:
        """Clear the seen-today set (call once per day if running long-lived)."""
        self._alerted.clear()
