"""Mute (silence) alerts for specific jobs for a configurable duration."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class MuteEntry:
    job_name: str
    muted_at: datetime
    muted_until: Optional[datetime]  # None means indefinite
    reason: str = ""

    def is_indefinite(self) -> bool:
        return self.muted_until is None

    def is_active(self, now: Optional[datetime] = None) -> bool:
        if self.is_indefinite():
            return True
        now = now or _utcnow()
        return now < self.muted_until

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "muted_at": self.muted_at.isoformat(),
            "muted_until": self.muted_until.isoformat() if self.muted_until else None,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MuteEntry":
        return cls(
            job_name=data["job_name"],
            muted_at=datetime.fromisoformat(data["muted_at"]),
            muted_until=(
                datetime.fromisoformat(data["muted_until"])
                if data.get("muted_until")
                else None
            ),
            reason=data.get("reason", ""),
        )


class MuteStore:
    def __init__(self, path: str) -> None:
        self._path = path

    def _load(self) -> Dict[str, MuteEntry]:
        if not os.path.exists(self._path):
            return {}
        with open(self._path) as fh:
            raw = json.load(fh)
        return {k: MuteEntry.from_dict(v) for k, v in raw.items()}

    def _save(self, entries: Dict[str, MuteEntry]) -> None:
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        with open(self._path, "w") as fh:
            json.dump({k: v.to_dict() for k, v in entries.items()}, fh, indent=2)

    def mute(self, entry: MuteEntry) -> None:
        entries = self._load()
        entries[entry.job_name] = entry
        self._save(entries)

    def unmute(self, job_name: str) -> None:
        entries = self._load()
        entries.pop(job_name, None)
        self._save(entries)

    def get(self, job_name: str) -> Optional[MuteEntry]:
        return self._load().get(job_name)

    def is_muted(self, job_name: str, now: Optional[datetime] = None) -> bool:
        entry = self.get(job_name)
        if entry is None:
            return False
        return entry.is_active(now)

    def all_active(self, now: Optional[datetime] = None) -> Dict[str, MuteEntry]:
        now = now or _utcnow()
        return {k: v for k, v in self._load().items() if v.is_active(now)}
