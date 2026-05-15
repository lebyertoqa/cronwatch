"""Lightweight trace context for correlating events across a single job run."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class TraceSpan:
    """A single timed span within a job execution trace."""

    name: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    metadata: Dict[str, str] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.ended_at is None:
            return None
        return (self.ended_at - self.started_at).total_seconds()

    def finish(self, **meta: str) -> "TraceSpan":
        self.ended_at = _utcnow()
        self.metadata.update(meta)
        return self


@dataclass
class TraceContext:
    """Trace context bound to a single job run."""

    job_name: str
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    started_at: datetime = field(default_factory=_utcnow)
    spans: List[TraceSpan] = field(default_factory=list)

    def start_span(self, name: str, **meta: str) -> TraceSpan:
        span = TraceSpan(name=name, started_at=_utcnow(), metadata=dict(meta))
        self.spans.append(span)
        return span

    def span_names(self) -> List[str]:
        return [s.name for s in self.spans]

    def total_span_seconds(self) -> float:
        return sum(
            s.duration_seconds for s in self.spans if s.duration_seconds is not None
        )


class TraceStore:
    """In-memory store of recent trace contexts keyed by trace_id."""

    def __init__(self, max_entries: int = 200) -> None:
        self._max = max_entries
        self._traces: Dict[str, TraceContext] = {}
        self._order: List[str] = []

    def record(self, ctx: TraceContext) -> None:
        if ctx.trace_id not in self._traces:
            self._order.append(ctx.trace_id)
        self._traces[ctx.trace_id] = ctx
        while len(self._order) > self._max:
            oldest = self._order.pop(0)
            self._traces.pop(oldest, None)

    def get(self, trace_id: str) -> Optional[TraceContext]:
        return self._traces.get(trace_id)

    def for_job(self, job_name: str) -> List[TraceContext]:
        return [t for t in self._traces.values() if t.job_name == job_name]

    def all(self) -> List[TraceContext]:
        return [self._traces[tid] for tid in self._order if tid in self._traces]
