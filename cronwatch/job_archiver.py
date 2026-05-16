"""Archive completed job history entries to a separate store."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from cronwatch.history import HistoryEntry, HistoryStore


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ArchivePolicy:
    """Defines which entries should be archived."""

    def __init__(self, older_than_days: int = 30) -> None:
        self.older_than_days = older_than_days

    def should_archive(self, entry: HistoryEntry, now: datetime | None = None) -> bool:
        if now is None:
            now = _utcnow()
        if not entry.finished_at:
            return False
        finished = datetime.fromisoformat(entry.finished_at)
        if finished.tzinfo is None:
            finished = finished.replace(tzinfo=timezone.utc)
        age = (now - finished).total_seconds()
        return age > self.older_than_days * 86400


class ArchiveStore:
    """Persists archived history entries as newline-delimited JSON."""

    def __init__(self, archive_dir: str | Path) -> None:
        self._dir = Path(archive_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, job_name: str) -> Path:
        safe = job_name.replace(os.sep, "_")
        return self._dir / f"{safe}.jsonl"

    def append(self, entry: HistoryEntry) -> None:
        path = self._path_for(entry.job_name)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.__dict__) + "\n")

    def entries_for(self, job_name: str) -> List[HistoryEntry]:
        path = self._path_for(job_name)
        if not path.exists():
            return []
        entries: List[HistoryEntry] = []
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    entries.append(HistoryEntry(**json.loads(line)))
        return entries


class JobArchiver:
    """Moves qualifying entries from a HistoryStore into an ArchiveStore."""

    def __init__(
        self,
        history: HistoryStore,
        archive: ArchiveStore,
        policy: ArchivePolicy | None = None,
    ) -> None:
        self._history = history
        self._archive = archive
        self._policy = policy or ArchivePolicy()

    def archive_job(self, job_name: str, now: datetime | None = None) -> int:
        """Archive old entries for *job_name*. Returns number archived."""
        entries = self._history.entries_for(job_name)
        archived = 0
        remaining: List[HistoryEntry] = []
        for entry in entries:
            if self._policy.should_archive(entry, now):
                self._archive.append(entry)
                archived += 1
            else:
                remaining.append(entry)
        if archived:
            self._history.replace_entries(job_name, remaining)
        return archived
