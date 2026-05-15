"""Job suppression: temporarily silence alerts for specific jobs."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SuppressionEntry:
    job_name: str
    reason: str
    suppressed_at: str
    expires_at: Optional[str] = None

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        if self.expires_at is None:
            return False
        now = now or _utcnow()
        return now >= datetime.fromisoformat(self.expires_at)

    def is_active(self, now: Optional[datetime] = None) -> bool:
        return not self.is_expired(now)


class SuppressionStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> Dict[str, SuppressionEntry]:
        if not self._path.exists():
            return {}
        raw = json.loads(self._path.read_text())
        return {
            name: SuppressionEntry(**entry)
            for name, entry in raw.items()
        }

    def _save(self, data: Dict[str, SuppressionEntry]) -> None:
        self._path.write_text(
            json.dumps({k: asdict(v) for k, v in data.items()}, indent=2)
        )

    def suppress(
        self,
        job_name: str,
        reason: str,
        expires_at: Optional[datetime] = None,
        now: Optional[datetime] = None,
    ) -> SuppressionEntry:
        now = now or _utcnow()
        entry = SuppressionEntry(
            job_name=job_name,
            reason=reason,
            suppressed_at=now.isoformat(),
            expires_at=expires_at.isoformat() if expires_at else None,
        )
        data = self._load()
        data[job_name] = entry
        self._save(data)
        return entry

    def release(self, job_name: str) -> bool:
        data = self._load()
        if job_name not in data:
            return False
        del data[job_name]
        self._save(data)
        return True

    def is_suppressed(self, job_name: str, now: Optional[datetime] = None) -> bool:
        data = self._load()
        entry = data.get(job_name)
        if entry is None:
            return False
        return entry.is_active(now)

    def active_suppressions(self, now: Optional[datetime] = None) -> List[SuppressionEntry]:
        data = self._load()
        return [e for e in data.values() if e.is_active(now)]

    def purge_expired(self, now: Optional[datetime] = None) -> int:
        data = self._load()
        before = len(data)
        data = {k: v for k, v in data.items() if v.is_active(now)}
        self._save(data)
        return before - len(data)
