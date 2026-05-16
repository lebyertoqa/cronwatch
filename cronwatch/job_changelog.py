"""Track configuration changes to job definitions over time."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ChangelogEntry:
    job_name: str
    changed_at: datetime
    field_name: str
    old_value: Any
    new_value: Any

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_name": self.job_name,
            "changed_at": self.changed_at.isoformat(),
            "field_name": self.field_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChangelogEntry":
        return cls(
            job_name=data["job_name"],
            changed_at=datetime.fromisoformat(data["changed_at"]),
            field_name=data["field_name"],
            old_value=data["old_value"],
            new_value=data["new_value"],
        )


@dataclass
class JobSnapshot:
    job_name: str
    captured_at: datetime
    fields: Dict[str, Any] = field(default_factory=dict)


class ChangelogStore:
    def __init__(self, path: str) -> None:
        self._path = path

    def _load(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self._path):
            return []
        with open(self._path, "r") as fh:
            return json.load(fh)

    def _save(self, entries: List[Dict[str, Any]]) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as fh:
            json.dump(entries, fh, indent=2)

    def record(self, entry: ChangelogEntry) -> None:
        entries = self._load()
        entries.append(entry.to_dict())
        self._save(entries)

    def entries_for(self, job_name: str) -> List[ChangelogEntry]:
        return [
            ChangelogEntry.from_dict(e)
            for e in self._load()
            if e["job_name"] == job_name
        ]

    def all_entries(self) -> List[ChangelogEntry]:
        return [ChangelogEntry.from_dict(e) for e in self._load()]


def diff_snapshots(
    before: JobSnapshot,
    after: JobSnapshot,
    store: ChangelogStore,
    now: Optional[datetime] = None,
) -> List[ChangelogEntry]:
    """Compare two snapshots and record any changed fields."""
    ts = now or _utcnow()
    recorded: List[ChangelogEntry] = []
    all_keys = set(before.fields) | set(after.fields)
    for key in sorted(all_keys):
        old_val = before.fields.get(key)
        new_val = after.fields.get(key)
        if old_val != new_val:
            entry = ChangelogEntry(
                job_name=after.job_name,
                changed_at=ts,
                field_name=key,
                old_value=old_val,
                new_value=new_val,
            )
            store.record(entry)
            recorded.append(entry)
    return recorded
