"""Sends alerts when jobs breach their SLA thresholds."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from cronwatch.alerting import Alerter
from cronwatch.job_sla import SLAStatus, SLATracker


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SLAAlerter:
    """Checks SLA status periodically and fires alerts for unhealthy jobs.

    Alerts are de-duplicated: a job that is already in violation will not
    trigger a second alert until it recovers and fails again.
    """

    def __init__(self, tracker: SLATracker, alerter: Alerter) -> None:
        self._tracker = tracker
        self._alerter = alerter
        self._alerted: Dict[str, bool] = {}  # job_name -> currently in violation

    def check(self, job_names: List[str]) -> List[SLAStatus]:
        """Evaluate SLAs, send alerts for new violations, return all violations."""
        violations: List[SLAStatus] = []

        for name in job_names:
            status = self._tracker.status_for(name)
            was_alerted = self._alerted.get(name, False)

            if not status.healthy:
                violations.append(status)
                if not was_alerted:
                    self._send_alert(status)
                    self._alerted[name] = True
            else:
                # Job recovered — reset so next violation triggers a fresh alert.
                self._alerted[name] = False

        return violations

    def _send_alert(self, status: SLAStatus) -> None:
        reasons: List[str] = []
        if not status.meets_success_rate:
            reasons.append(
                f"success rate {status.success_rate:.0%} below threshold"
            )
        if not status.meets_duration:
            reasons.append(
                f"avg duration {status.avg_duration_seconds:.1f}s exceeds limit"
            )

        subject = f"[cronwatch] SLA breach: {status.job_name}"
        body = (
            f"Job '{status.job_name}' has breached its SLA over the last "
            f"{status.window_hours}h.\n\n"
            f"  Runs      : {status.total_runs}\n"
            f"  Successes : {status.successful_runs}\n"
            f"  Reason(s) : {'; '.join(reasons)}\n"
        )
        self._alerter.send(subject=subject, body=body)
