"""Heartbeat tracking for cron jobs.

Records the last successful completion time for each job and exposes
whether a job is considered "alive" based on a configurable TTL.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class HeartbeatEntry:
    job_name: str
    last_success: datetime

    def age_seconds(self, now: Optional[datetime] = None) -> float:
        now = now or _utcnow()
        return (now - self.last_success).total_seconds()

    def is_alive(self, ttl_seconds: float, now: Optional[datetime] = None) -> bool:
        return self.age_seconds(now) <= ttl_seconds


class HeartbeatStore:
    def __init__(self, directory: str) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        safe = job_name.replace(os.sep, "_").replace(" ", "_")
        return self._dir / f"{safe}.heartbeat.json"

    def record(self, job_name: str, ts: Optional[datetime] = None) -> HeartbeatEntry:
        ts = ts or _utcnow()
        entry = HeartbeatEntry(job_name=job_name, last_success=ts)
        payload = {"job_name": job_name, "last_success": ts.isoformat()}
        self._path(job_name).write_text(json.dumps(payload))
        return entry

    def get(self, job_name: str) -> Optional[HeartbeatEntry]:
        p = self._path(job_name)
        if not p.exists():
            return None
        data = json.loads(p.read_text())
        return HeartbeatEntry(
            job_name=data["job_name"],
            last_success=datetime.fromisoformat(data["last_success"]),
        )

    def all(self) -> Dict[str, HeartbeatEntry]:
        result: Dict[str, HeartbeatEntry] = {}
        for p in self._dir.glob("*.heartbeat.json"):
            data = json.loads(p.read_text())
            name = data["job_name"]
            result[name] = HeartbeatEntry(
                job_name=name,
                last_success=datetime.fromisoformat(data["last_success"]),
            )
        return result

    def remove(self, job_name: str) -> None:
        p = self._path(job_name)
        if p.exists():
            p.unlink()
