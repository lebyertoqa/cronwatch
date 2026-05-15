"""Checksum tracking for job command definitions.

Detects when a job's command changes between runs so operators can be
alerted that a previously-recorded history may no longer be comparable.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


def _checksum(command: str) -> str:
    """Return a short SHA-256 hex digest for *command*."""
    return hashlib.sha256(command.encode()).hexdigest()[:16]


@dataclass
class ChecksumEntry:
    job_name: str
    command: str
    digest: str

    @staticmethod
    def from_command(job_name: str, command: str) -> "ChecksumEntry":
        return ChecksumEntry(job_name=job_name, command=command, digest=_checksum(command))


class ChecksumStore:
    """Persist and compare command checksums across daemon restarts."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._data: Dict[str, str] = self._load()

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    def _load(self) -> Dict[str, str]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2))

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def record(self, job_name: str, command: str) -> None:
        """Store the current checksum for *job_name*."""
        self._data[job_name] = _checksum(command)
        self._save()

    def get(self, job_name: str) -> Optional[str]:
        """Return the stored digest for *job_name*, or ``None``."""
        return self._data.get(job_name)

    def changed(self, job_name: str, command: str) -> bool:
        """Return ``True`` if *command* differs from the stored checksum."""
        stored = self.get(job_name)
        if stored is None:
            return False  # no history — not a change
        return stored != _checksum(command)

    def all_entries(self) -> Dict[str, str]:
        """Return a copy of the raw digest mapping."""
        return dict(self._data)
