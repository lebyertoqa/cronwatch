"""Snapshot the last known good execution result for each job.

A 'good' result is any successful execution. Snapshots are persisted to
a JSON file so they survive daemon restarts.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from cronwatch.executor import ExecutionResult


@dataclass
class Snapshot:
    job_name: str
    command: str
    exit_code: int
    started_at: str   # ISO-8601
    duration: float

    @staticmethod
    def from_result(result: ExecutionResult) -> "Snapshot":
        return Snapshot(
            job_name=result.job_name,
            command=result.command,
            exit_code=result.exit_code,
            started_at=result.started_at.isoformat(),
            duration=result.duration,
        )

    def started_at_dt(self) -> datetime:
        return datetime.fromisoformat(self.started_at).replace(tzinfo=timezone.utc)


class SnapshotStore:
    """Persist and retrieve last-good snapshots for each job."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._data: Dict[str, Snapshot] = self._load()

    # ------------------------------------------------------------------
    def record(self, result: ExecutionResult) -> None:
        """Update the snapshot only when the job succeeded."""
        if result.exit_code != 0:
            return
        self._data[result.job_name] = Snapshot.from_result(result)
        self._persist()

    def get(self, job_name: str) -> Optional[Snapshot]:
        return self._data.get(job_name)

    def all(self) -> Dict[str, Snapshot]:
        return dict(self._data)

    def clear(self, job_name: str) -> None:
        """Remove the snapshot for a job (e.g. after it is deleted)."""
        self._data.pop(job_name, None)
        self._persist()

    # ------------------------------------------------------------------
    def _load(self) -> Dict[str, Snapshot]:
        if not self._path.exists():
            return {}
        try:
            raw = json.loads(self._path.read_text())
            return {k: Snapshot(**v) for k, v in raw.items()}
        except Exception:
            return {}

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps({k: asdict(v) for k, v in self._data.items()}, indent=2))
        os.replace(tmp, self._path)
