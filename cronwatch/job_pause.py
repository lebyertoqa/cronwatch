"""Pause/resume control for individual cron jobs."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PauseEntry:
    job_name: str
    paused_at: datetime
    reason: Optional[str] = None
    resume_at: Optional[datetime] = None

    def is_indefinite(self) -> bool:
        return self.resume_at is None

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        if self.resume_at is None:
            return False
        return (now or _utcnow()) >= self.resume_at


class PauseStore:
    """Persists pause state for jobs using a JSON file."""

    def __init__(self, state_path: Path) -> None:
        self._path = state_path
        self._entries: Dict[str, PauseEntry] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(
                f"Failed to load pause state from {self._path}: {exc}"
            ) from exc
        for name, data in raw.items():
            self._entries[name] = PauseEntry(
                job_name=name,
                paused_at=datetime.fromisoformat(data["paused_at"]),
                reason=data.get("reason"),
                resume_at=(
                    datetime.fromisoformat(data["resume_at"])
                    if data.get("resume_at")
                    else None
                ),
            )

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            name: {
                "paused_at": e.paused_at.isoformat(),
                "reason": e.reason,
                "resume_at": e.resume_at.isoformat() if e.resume_at else None,
            }
            for name, e in self._entries.items()
        }
        self._path.write_text(json.dumps(data, indent=2))

    def pause(self, job_name: str, reason: Optional[str] = None,
               resume_at: Optional[datetime] = None) -> PauseEntry:
        entry = PauseEntry(
            job_name=job_name,
            paused_at=_utcnow(),
            reason=reason,
            resume_at=resume_at,
        )
        self._entries[job_name] = entry
        self._save()
        return entry

    def resume(self, job_name: str) -> bool:
        if job_name not in self._entries:
            return False
        del self._entries[job_name]
        self._save()
        return True

    def is_paused(self, job_name: str, now: Optional[datetime] = None) -> bool:
        entry = self._entries.get(job_name)
        if entry is None:
            return False
        if entry.is_expired(now):
            del self._entries[job_name]
            self._save()
            return False
        return True

    def get(self, job_name: str) -> Optional[PauseEntry]:
        return self._entries.get(job_name)

    def all_paused(self) -> list[PauseEntry]:
        return list(self._entries.values())
