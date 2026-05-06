"""Audit log: append-only record of significant cronwatch events."""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class AuditEvent:
    timestamp: str
    event: str          # e.g. 'job_started', 'job_finished', 'alert_sent'
    job_name: str
    detail: Optional[str] = None

    @staticmethod
    def now(event: str, job_name: str, detail: Optional[str] = None) -> "AuditEvent":
        return AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event=event,
            job_name=job_name,
            detail=detail,
        )


class AuditLog:
    """Thread-safe append-only audit log backed by a JSONL file."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: AuditEvent) -> None:
        """Append *event* to the log file."""
        line = json.dumps(asdict(event), separators=(",", ":"))
        with self._lock:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    def read_all(self) -> List[AuditEvent]:
        """Return every event recorded so far, oldest first."""
        if not self._path.exists():
            return []
        events: List[AuditEvent] = []
        with self._lock:
            with self._path.open("r", encoding="utf-8") as fh:
                for raw in fh:
                    raw = raw.strip()
                    if raw:
                        data = json.loads(raw)
                        events.append(AuditEvent(**data))
        return events

    def read_for_job(self, job_name: str) -> List[AuditEvent]:
        """Return only events that belong to *job_name*."""
        return [e for e in self.read_all() if e.job_name == job_name]
