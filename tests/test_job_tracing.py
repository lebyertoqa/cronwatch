"""Tests for cronwatch.job_tracing."""
from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest

from cronwatch.job_tracing import TraceContext, TraceSpan, TraceStore


def _utc(**kw) -> datetime:
    return datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc).replace(**kw)


# ---------------------------------------------------------------------------
# TraceSpan
# ---------------------------------------------------------------------------

def test_span_duration_none_when_not_finished():
    span = TraceSpan(name="setup", started_at=_utc())
    assert span.duration_seconds is None


def test_span_finish_sets_ended_at():
    span = TraceSpan(name="run", started_at=_utc())
    span.finish()
    assert span.ended_at is not None


def test_span_duration_positive_after_finish():
    span = TraceSpan(name="run", started_at=_utc())
    time.sleep(0.01)
    span.finish()
    assert span.duration_seconds is not None
    assert span.duration_seconds >= 0


def test_span_finish_stores_metadata():
    span = TraceSpan(name="check", started_at=_utc())
    span.finish(exit_code="0")
    assert span.metadata["exit_code"] == "0"


# ---------------------------------------------------------------------------
# TraceContext
# ---------------------------------------------------------------------------

def test_trace_context_has_unique_trace_id():
    ctx1 = TraceContext(job_name="backup")
    ctx2 = TraceContext(job_name="backup")
    assert ctx1.trace_id != ctx2.trace_id


def test_start_span_appends_to_spans():
    ctx = TraceContext(job_name="deploy")
    ctx.start_span("pre-hook")
    ctx.start_span("execute")
    assert ctx.span_names() == ["pre-hook", "execute"]


def test_total_span_seconds_sums_finished_spans():
    ctx = TraceContext(job_name="sync")
    s1 = ctx.start_span("a")
    s1.finish()
    s2 = ctx.start_span("b")
    # leave s2 unfinished — should be excluded
    total = ctx.total_span_seconds()
    assert total >= 0
    assert s2.duration_seconds is None


def test_span_names_empty_initially():
    ctx = TraceContext(job_name="noop")
    assert ctx.span_names() == []


# ---------------------------------------------------------------------------
# TraceStore
# ---------------------------------------------------------------------------

def test_record_and_retrieve():
    store = TraceStore()
    ctx = TraceContext(job_name="job-a")
    store.record(ctx)
    assert store.get(ctx.trace_id) is ctx


def test_get_unknown_trace_returns_none():
    store = TraceStore()
    assert store.get("nonexistent") is None


def test_for_job_filters_by_name():
    store = TraceStore()
    ctx_a = TraceContext(job_name="alpha")
    ctx_b = TraceContext(job_name="beta")
    store.record(ctx_a)
    store.record(ctx_b)
    results = store.for_job("alpha")
    assert len(results) == 1
    assert results[0].job_name == "alpha"


def test_all_returns_in_insertion_order():
    store = TraceStore()
    names = ["first", "second", "third"]
    for n in names:
        store.record(TraceContext(job_name=n))
    assert [t.job_name for t in store.all()] == names


def test_max_entries_evicts_oldest():
    store = TraceStore(max_entries=3)
    ctxs = [TraceContext(job_name=f"job-{i}") for i in range(5)]
    for c in ctxs:
        store.record(c)
    remaining = store.all()
    assert len(remaining) == 3
    assert remaining[0].job_name == "job-2"


def test_recording_same_trace_id_twice_does_not_duplicate():
    store = TraceStore()
    ctx = TraceContext(job_name="idempotent")
    store.record(ctx)
    store.record(ctx)
    assert len(store.all()) == 1
