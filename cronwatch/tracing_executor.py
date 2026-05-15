"""Executor wrapper that attaches a TraceContext to every job run."""
from __future__ import annotations

from typing import Optional

from cronwatch.executor import ExecutionResult, run_job
from cronwatch.config import JobConfig
from cronwatch.job_tracing import TraceContext, TraceStore


class _InnerExecutor:
    """Protocol-compatible shim so TracingExecutor can wrap any executor."""

    def run(self, job: JobConfig) -> ExecutionResult:
        return run_job(job)


class TracingExecutor:
    """Wraps an executor and records a TraceContext for each run."""

    def __init__(
        self,
        inner: Optional[_InnerExecutor] = None,
        store: Optional[TraceStore] = None,
    ) -> None:
        self._inner = inner or _InnerExecutor()
        self._store = store or TraceStore()

    @property
    def store(self) -> TraceStore:
        return self._store

    def run(self, job: JobConfig) -> ExecutionResult:
        ctx = TraceContext(job_name=job.name)

        setup_span = ctx.start_span("setup")
        setup_span.finish()

        exec_span = ctx.start_span("execute")
        result = self._inner.run(job)
        exec_span.finish(
            success=str(result.success),
            exit_code=str(result.returncode) if hasattr(result, "returncode") else "",
        )

        ctx.start_span("teardown").finish()

        self._store.record(ctx)
        return result


def build_tracing_executor(
    inner: Optional[_InnerExecutor] = None,
    store: Optional[TraceStore] = None,
) -> TracingExecutor:
    """Factory used by the main pipeline to construct a TracingExecutor."""
    return TracingExecutor(inner=inner, store=store or TraceStore())
