"""Persistent history of job execution results."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional

from cronwatch.executor import ExecutionResult


@dataclass
class HistoryEntry:
    job_name: str
    success: bool
    exit_code: int
    duration: float
    started_at: str
    finished_at: Optional[str] = None
    stdout: str = ""
    stderr: str = ""

    @staticmethod
    def from_result(result: ExecutionResult) -> "HistoryEntry":
        return HistoryEntry(
            job_name=result.job_name,
            success=result.success,
            exit_code=result.exit_code,
            duration=result.duration,
            started_at=result.started_at.isoformat(),
            finished_at=result.finished_at.isoformat() if result.finished_at else None,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
        )


class HistoryStore:
    def __init__(self, history_dir: str | Path) -> None:
        self._dir = Path(history_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, job_name: str) -> Path:
        safe = job_name.replace(os.sep, "_")
        return self._dir / f"{safe}.jsonl"

    def _load_raw(self, job_name: str) -> List[dict]:
        path = self._path_for(job_name)
        if not path.exists():
            return []
        rows: List[dict] = []
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    def record(self, result: ExecutionResult) -> HistoryEntry:
        entry = HistoryEntry.from_result(result)
        path = self._path_for(result.job_name)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(entry)) + "\n")
        return entry

    def entries_for(self, job_name: str) -> List[HistoryEntry]:
        return [HistoryEntry(**row) for row in self._load_raw(job_name)]

    def replace_entries(self, job_name: str, entries: List[HistoryEntry]) -> None:
        """Overwrite stored entries for *job_name* with *entries*."""
        path = self._path_for(job_name)
        with path.open("w", encoding="utf-8") as fh:
            for entry in entries:
                fh.write(json.dumps(asdict(entry)) + "\n")

    def all_entries(self) -> List[HistoryEntry]:
        entries: List[HistoryEntry] = []
        for path in sorted(self._dir.glob("*.jsonl")):
            with path.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        entries.append(HistoryEntry(**json.loads(line)))
        return entries
