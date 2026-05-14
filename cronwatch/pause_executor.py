"""Executor wrapper that skips paused jobs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol

from cronwatch.executor import ExecutionResult
from cronwatch.job_pause import PauseStore


class _InnerExecutor(Protocol):
    def run(self, job) -> ExecutionResult:
        ...


@dataclass
class PauseSkipResult:
    job_name: str
    reason: Optional[str]

    @property
    def skipped(self) -> bool:
        return True

    def __str__(self) -> str:
        msg = f"Job '{self.job_name}' is paused"
        if self.reason:
            msg += f": {self.reason}"
        return msg


class PauseAwareExecutor:
    """Wraps an executor and skips execution for paused jobs."""

    def __init__(self, inner: _InnerExecutor, store: PauseStore) -> None:
        self._inner = inner
        self._store = store

    def run(self, job) -> ExecutionResult | PauseSkipResult:
        if self._store.is_paused(job.name):
            entry = self._store.get(job.name)
            reason = entry.reason if entry else None
            return PauseSkipResult(job_name=job.name, reason=reason)
        return self._inner.run(job)


def build_pause_aware_executor(
    inner: _InnerExecutor,
    store: PauseStore,
) -> PauseAwareExecutor:
    return PauseAwareExecutor(inner=inner, store=store)
