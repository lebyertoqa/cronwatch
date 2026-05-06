"""Prune old history entries to keep storage bounded."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from cronwatch.history import HistoryStore

log = logging.getLogger(__name__)


def prune_older_than(
    store: HistoryStore,
    job_name: str,
    cutoff: datetime,
) -> int:
    """Remove entries for *job_name* that finished before *cutoff*.

    Returns the number of entries removed.
    """
    entries = store.get(job_name)
    kept = [e for e in entries if e.finished_at >= cutoff]
    removed = len(entries) - len(kept)
    if removed:
        store._data[job_name] = [e._asdict() if hasattr(e, "_asdict") else vars(e) for e in kept]  # type: ignore[attr-defined]
        store._flush()
        log.info("Pruned %d old entries for job '%s'", removed, job_name)
    return removed


def prune_excess(
    store: HistoryStore,
    job_name: str,
    max_entries: int,
) -> int:
    """Keep only the *max_entries* most-recent entries for *job_name*.

    Returns the number of entries removed.
    """
    if max_entries <= 0:
        raise ValueError("max_entries must be a positive integer")
    entries = store.get(job_name)
    if len(entries) <= max_entries:
        return 0
    kept = entries[-max_entries:]
    removed = len(entries) - len(kept)
    store._data[job_name] = [vars(e) for e in kept]  # type: ignore[attr-defined]
    store._flush()
    log.info("Pruned %d excess entries for job '%s'", removed, job_name)
    return removed


class RetentionPolicy:
    """Applies age- and count-based retention rules to a HistoryStore."""

    def __init__(
        self,
        store: HistoryStore,
        max_age_days: Optional[int] = None,
        max_entries: Optional[int] = None,
    ) -> None:
        self.store = store
        self.max_age_days = max_age_days
        self.max_entries = max_entries

    def apply(self, job_name: str) -> int:
        """Apply all configured rules to *job_name*. Returns total removed."""
        removed = 0
        if self.max_age_days is not None:
            cutoff = datetime.now(tz=timezone.utc) - timedelta(days=self.max_age_days)
            removed += prune_older_than(self.store, job_name, cutoff)
        if self.max_entries is not None:
            removed += prune_excess(self.store, job_name, self.max_entries)
        return removed

    def apply_all(self) -> dict[str, int]:
        """Apply rules to every job present in the store."""
        results: dict[str, int] = {}
        for job_name in list(self.store._data.keys()):  # type: ignore[attr-defined]
            results[job_name] = self.apply(job_name)
        return results
