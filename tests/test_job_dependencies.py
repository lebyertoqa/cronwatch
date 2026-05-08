"""Tests for cronwatch.job_dependencies."""
from __future__ import annotations

import pytest

from cronwatch.config import JobConfig
from cronwatch.job_dependencies import DependencyCycleError, DependencyGraph


def _job(name: str, depends_on=None) -> JobConfig:
    return JobConfig(
        name=name,
        command=f"echo {name}",
        schedule="* * * * *",
        depends_on=depends_on or [],
    )


# ---------------------------------------------------------------------------
# DependencyGraph.from_jobs
# ---------------------------------------------------------------------------

def test_from_jobs_builds_graph():
    jobs = [_job("a"), _job("b", depends_on=["a"])]
    g = DependencyGraph.from_jobs(jobs)
    assert g.dependencies_of("b") == {"a"}
    assert g.dependencies_of("a") == set()


def test_from_jobs_no_deps():
    jobs = [_job("x"), _job("y")]
    g = DependencyGraph.from_jobs(jobs)
    assert g.dependencies_of("x") == set()
    assert g.dependencies_of("y") == set()


# ---------------------------------------------------------------------------
# topological_order
# ---------------------------------------------------------------------------

def test_topological_order_independent_jobs():
    jobs = [_job("a"), _job("b"), _job("c")]
    g = DependencyGraph.from_jobs(jobs)
    order = g.topological_order()
    assert set(order) == {"a", "b", "c"}


def test_topological_order_respects_dependency():
    jobs = [_job("b", depends_on=["a"]), _job("a")]
    g = DependencyGraph.from_jobs(jobs)
    order = g.topological_order()
    assert order.index("a") < order.index("b")


def test_topological_order_chain():
    jobs = [_job("c", depends_on=["b"]), _job("b", depends_on=["a"]), _job("a")]
    g = DependencyGraph.from_jobs(jobs)
    order = g.topological_order()
    assert order.index("a") < order.index("b") < order.index("c")


def test_topological_order_raises_on_cycle():
    # a -> b -> a
    g = DependencyGraph(_deps={"a": {"b"}, "b": {"a"}})
    with pytest.raises(DependencyCycleError):
        g.topological_order()


def test_topological_order_raises_on_self_loop():
    g = DependencyGraph(_deps={"a": {"a"}})
    with pytest.raises(DependencyCycleError):
        g.topological_order()


# ---------------------------------------------------------------------------
# ready_to_run
# ---------------------------------------------------------------------------

def test_ready_to_run_no_deps_all_ready():
    jobs = [_job("a"), _job("b")]
    g = DependencyGraph.from_jobs(jobs)
    ready = g.ready_to_run(completed=set())
    assert set(ready) == {"a", "b"}


def test_ready_to_run_waits_for_dep():
    jobs = [_job("a"), _job("b", depends_on=["a"])]
    g = DependencyGraph.from_jobs(jobs)
    assert "b" not in g.ready_to_run(completed=set())
    assert "b" in g.ready_to_run(completed={"a"})


def test_ready_to_run_excludes_already_completed():
    jobs = [_job("a"), _job("b")]
    g = DependencyGraph.from_jobs(jobs)
    ready = g.ready_to_run(completed={"a"})
    assert "a" not in ready
    assert "b" in ready


def test_ready_to_run_multiple_deps_all_must_complete():
    jobs = [_job("a"), _job("b"), _job("c", depends_on=["a", "b"])]
    g = DependencyGraph.from_jobs(jobs)
    assert "c" not in g.ready_to_run(completed={"a"})
    assert "c" in g.ready_to_run(completed={"a", "b"})
