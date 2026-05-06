"""Thin helpers that integrate AuditLog with the executor and alerter."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from cronwatch.audit import AuditEvent, AuditLog
from cronwatch.executor import ExecutionResult


class AuditingExecutor:
    """Wraps a callable that runs a job and records start/finish events."""

    def __init__(self, run_fn, audit_log: AuditLog) -> None:
        self._run = run_fn
        self._log = audit_log

    def run(self, job) -> ExecutionResult:
        self._log.record(AuditEvent.now("job_started", job.name))
        result: ExecutionResult = self._run(job)
        detail = (
            f"exit_code={result.exit_code} duration={result.duration:.3f}s"
        )
        event_name = "job_succeeded" if result.success else "job_failed"
        self._log.record(AuditEvent.now(event_name, job.name, detail=detail))
        return result


def record_alert_sent(
    audit_log: AuditLog,
    job_name: str,
    recipient: Optional[str] = None,
) -> None:
    """Record that an alert was dispatched for *job_name*."""
    detail = f"recipient={recipient}" if recipient else None
    audit_log.record(AuditEvent.now("alert_sent", job_name, detail=detail))


def build_audit_log(data_dir: str | Path) -> AuditLog:
    """Convenience factory used by __main__ to create the shared AuditLog."""
    return AuditLog(Path(data_dir) / "audit.jsonl")
