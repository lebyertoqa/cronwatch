"""Report on jobs that have never succeeded or regressed since their snapshot."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Sequence

from cronwatch.executor import ExecutionResult
from cronwatch.job_snapshot import Snapshot, SnapshotStore


@dataclass
class SnapshotReport:
    job_name: str
    last_good: Snapshot
    current_exit_code: int
    is_regression: bool  # succeeded before, now failing


class SnapshotReporter:
    """Compare fresh results against stored snapshots."""

    def __init__(self, store: SnapshotStore) -> None:
        self._store = store

    def analyse(self, results: Sequence[ExecutionResult]) -> List[SnapshotReport]:
        """Return a report for every result that is a regression."""
        reports: List[SnapshotReport] = []
        for result in results:
            if result.exit_code == 0:
                continue  # not a failure, no regression
            snapshot = self._store.get(result.job_name)
            if snapshot is None:
                continue  # never had a good run — not a regression
            reports.append(
                SnapshotReport(
                    job_name=result.job_name,
                    last_good=snapshot,
                    current_exit_code=result.exit_code,
                    is_regression=True,
                )
            )
        return reports

    def never_succeeded(self, all_job_names: Sequence[str]) -> List[str]:
        """Return names of jobs that have no recorded good run."""
        return [n for n in all_job_names if self._store.get(n) is None]

    def last_good_age_seconds(self, job_name: str) -> float | None:
        """Seconds since the last good run, or None if no snapshot exists."""
        snap = self._store.get(job_name)
        if snap is None:
            return None
        now = datetime.now(tz=timezone.utc)
        return (now - snap.started_at_dt()).total_seconds()
