"""Execution window enforcement for cron jobs.

Allows jobs to be restricted to specific time windows (e.g. only run
between 08:00 and 18:00 UTC).  Jobs attempted outside their window are
marked as skipped rather than executed.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class WindowPolicy:
    """Per-job execution window configuration."""

    # Mapping of job name -> list of (start, end) time pairs (UTC, inclusive).
    windows: dict = field(default_factory=dict)

    def windows_for(self, job_name: str) -> List[Tuple[datetime.time, datetime.time]]:
        """Return the list of allowed windows for *job_name*.

        Returns an empty list when no window is configured, meaning the job
        may run at any time.
        """
        return list(self.windows.get(job_name, []))


def _utcnow() -> datetime.datetime:
    return datetime.datetime.utcnow()


def parse_window(raw: str) -> Tuple[datetime.time, datetime.time]:
    """Parse a window string of the form ``'HH:MM-HH:MM'``.

    Raises ``ValueError`` when the format is invalid.
    """
    try:
        start_str, end_str = raw.split("-", 1)
        start = datetime.time.fromisoformat(start_str.strip())
        end = datetime.time.fromisoformat(end_str.strip())
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Invalid window string {raw!r}: {exc}") from exc
    return start, end


def within_window(
    windows: List[Tuple[datetime.time, datetime.time]],
    at: Optional[datetime.datetime] = None,
) -> bool:
    """Return ``True`` when *at* falls within at least one of *windows*.

    If *windows* is empty the job is considered unrestricted and ``True`` is
    always returned.  *at* defaults to the current UTC time.
    """
    if not windows:
        return True
    check_time = (at or _utcnow()).time()
    for start, end in windows:
        if start <= end:
            if start <= check_time <= end:
                return True
        else:
            # Window wraps midnight (e.g. 22:00-06:00)
            if check_time >= start or check_time <= end:
                return True
    return False


@dataclass
class WindowSkipResult:
    """Returned by :class:`WindowGuard` when a job is outside its window."""

    job_name: str
    windows: List[Tuple[datetime.time, datetime.time]]
    checked_at: datetime.datetime

    @property
    def skipped(self) -> bool:  # noqa: D401
        return True

    def __str__(self) -> str:
        windows_str = ", ".join(f"{s}-{e}" for s, e in self.windows)
        return (
            f"Job '{self.job_name}' skipped: outside allowed window(s) [{windows_str}] "
            f"at {self.checked_at.strftime('%H:%M')} UTC"
        )
