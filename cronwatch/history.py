"""Persistent execution history for cron jobs."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from cronwatch.executor import ExecutionResult

DEFAULT_HISTORY_PATH = Path("/var/lib/cronwatch/history.json")
_MAX_ENTRIES_PER_JOB = 50


@dataclass
class HistoryEntry:
    job_name: str
    started_at: str  # ISO-8601
    duration_seconds: float
    exit_code: int
    succeeded: bool
    stdout_tail: str
    stderr_tail: str

    @classmethod
    def from_result(cls, result: ExecutionResult) -> "HistoryEntry":
        return cls(
            job_name=result.job_name,
            started_at=result.started_at.isoformat(),
            duration_seconds=round(result.duration_seconds, 3),
            exit_code=result.exit_code,
            succeeded=result.succeeded,
            stdout_tail=result.stdout[-500:] if result.stdout else "",
            stderr_tail=result.stderr[-500:] if result.stderr else "",
        )


class HistoryStore:
    """Read/write execution history to a JSON file."""

    def __init__(self, path: Path = DEFAULT_HISTORY_PATH) -> None:
        self.path = Path(path)

    def _load_raw(self) -> dict:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def _save_raw(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, self.path)

    def record(self, result: ExecutionResult) -> None:
        """Append a result to the history, pruning old entries."""
        data = self._load_raw()
        entry = HistoryEntry.from_result(result)
        entries = data.get(result.job_name, [])
        entries.append(asdict(entry))
        entries = entries[-_MAX_ENTRIES_PER_JOB:]
        data[result.job_name] = entries
        self._save_raw(data)

    def get(self, job_name: str) -> List[HistoryEntry]:
        """Return history entries for a specific job, oldest first."""
        data = self._load_raw()
        return [
            HistoryEntry(**e) for e in data.get(job_name, [])
        ]

    def last_failure(self, job_name: str) -> Optional[HistoryEntry]:
        """Return the most recent failed entry for a job, or None."""
        for entry in reversed(self.get(job_name)):
            if not entry.succeeded:
                return entry
        return None
