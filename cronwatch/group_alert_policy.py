"""Alerting policy that operates at the job-group level."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwatch.alerting import Alerter
from cronwatch.group_reporter import GroupReport, GroupSummary


@dataclass
class GroupAlertPolicy:
    """Fire an alert when a group's failure rate exceeds a threshold."""
    failure_rate_threshold: float = 0.5
    min_runs: int = 1
    alert_once_per_group: bool = True
    _alerted: Dict[str, bool] = field(default_factory=dict, init=False, repr=False)

    def should_alert(self, summary: GroupSummary) -> bool:
        if summary.total < self.min_runs:
            return False
        failure_rate = 1.0 - summary.success_rate
        if failure_rate < self.failure_rate_threshold:
            return False
        if self.alert_once_per_group and self._alerted.get(summary.group_key):
            return False
        return True

    def mark_alerted(self, group_key: str) -> None:
        self._alerted[group_key] = True

    def reset(self, group_key: Optional[str] = None) -> None:
        if group_key is None:
            self._alerted.clear()
        else:
            self._alerted.pop(group_key, None)


def evaluate_group_alerts(
    report: GroupReport,
    policy: GroupAlertPolicy,
    alerter: Alerter,
) -> List[str]:
    """Check every group summary; send alerts and return alerted group keys."""
    from cronwatch.executor import ExecutionResult  # local import to avoid cycles

    alerted: List[str] = []
    for key, summary in report.summaries.items():
        if not policy.should_alert(summary):
            continue
        subject = f"[cronwatch] Group '{key}' failure rate above threshold"
        body = (
            f"Group: {key}\n"
            f"Total runs: {summary.total}\n"
            f"Failures: {summary.failures}\n"
            f"Success rate: {summary.success_rate:.1%}\n"
            f"Jobs: {', '.join(summary.job_names)}"
        )
        # Reuse alerter.send with a synthetic result-like object
        fake_result = _FakeResult(job_name=f"group:{key}", output=body)
        alerter.send(fake_result)  # type: ignore[arg-type]
        policy.mark_alerted(key)
        alerted.append(key)
    return alerted


@dataclass
class _FakeResult:
    """Minimal stand-in so Alerter.send can be called with group context."""
    job_name: str
    output: str
    success: bool = False
    exit_code: int = 1
    duration: float = 0.0
