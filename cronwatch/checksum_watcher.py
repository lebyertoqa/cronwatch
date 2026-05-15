"""Watches for command changes across jobs and emits alerts.

On each ``check`` call the watcher compares every job's current command
against its stored checksum.  When a change is detected an alert is sent
once (the new checksum is then recorded so subsequent checks are silent).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from cronwatch.alerting import Alerter
from cronwatch.config import JobConfig
from cronwatch.job_checksum import ChecksumStore


@dataclass
class CommandChange:
    job_name: str
    old_digest: str | None
    new_digest: str
    command: str


class ChecksumWatcher:
    """Detect and alert on job command changes."""

    def __init__(
        self,
        store: ChecksumStore,
        alerter: Alerter,
        jobs: Sequence[JobConfig],
    ) -> None:
        self._store = store
        self._alerter = alerter
        self._jobs = list(jobs)

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------

    def check(self) -> List[CommandChange]:
        """Inspect all jobs; alert and return any that have changed."""
        changes: List[CommandChange] = []
        for job in self._jobs:
            command = job.command
            if not self._store.changed(job.name, command):
                # First-time record or no change — ensure digest is stored.
                if self._store.get(job.name) is None:
                    self._store.record(job.name, command)
                continue

            old = self._store.get(job.name)
            self._store.record(job.name, command)
            from cronwatch.job_checksum import _checksum
            change = CommandChange(
                job_name=job.name,
                old_digest=old,
                new_digest=_checksum(command),
                command=command,
            )
            changes.append(change)
            self._alert(change)

        return changes

    # ------------------------------------------------------------------
    # private
    # ------------------------------------------------------------------

    def _alert(self, change: CommandChange) -> None:
        subject = f"[cronwatch] Command changed: {change.job_name}"
        body = (
            f"Job '{change.job_name}' command has changed.\n"
            f"Old digest : {change.old_digest}\n"
            f"New digest : {change.new_digest}\n"
            f"New command: {change.command}"
        )
        self._alerter.send(subject=subject, body=body)
