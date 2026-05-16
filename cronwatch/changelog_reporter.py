"""Summarise job configuration changes from the changelog store."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from cronwatch.job_changelog import ChangelogEntry, ChangelogStore


@dataclass
class ChangelogSummary:
    job_name: str
    total_changes: int
    last_changed_at: Optional[datetime]
    changed_fields: List[str]

    @property
    def has_changes(self) -> bool:
        return self.total_changes > 0


@dataclass
class ChangelogReport:
    summaries: List[ChangelogSummary]

    @property
    def total_jobs_with_changes(self) -> int:
        return sum(1 for s in self.summaries if s.has_changes)

    @property
    def total_changes(self) -> int:
        return sum(s.total_changes for s in self.summaries)

    def summary_for(self, job_name: str) -> Optional[ChangelogSummary]:
        for s in self.summaries:
            if s.job_name == job_name:
                return s
        return None


def _summarise_entries(job_name: str, entries: List[ChangelogEntry]) -> ChangelogSummary:
    if not entries:
        return ChangelogSummary(
            job_name=job_name,
            total_changes=0,
            last_changed_at=None,
            changed_fields=[],
        )
    last = max(entries, key=lambda e: e.changed_at)
    fields = sorted({e.field_name for e in entries})
    return ChangelogSummary(
        job_name=job_name,
        total_changes=len(entries),
        last_changed_at=last.changed_at,
        changed_fields=fields,
    )


def build_changelog_report(store: ChangelogStore) -> ChangelogReport:
    all_entries = store.all_entries()
    grouped: Dict[str, List[ChangelogEntry]] = {}
    for entry in all_entries:
        grouped.setdefault(entry.job_name, []).append(entry)
    summaries = [
        _summarise_entries(job_name, job_entries)
        for job_name, job_entries in sorted(grouped.items())
    ]
    return ChangelogReport(summaries=summaries)
