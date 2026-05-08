"""Dependency resolution for cron jobs.

Allows jobs to declare that they must run after other jobs have succeeded.
Provides topological ordering and cycle detection.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set

from cronwatch.config import JobConfig


class DependencyCycleError(Exception):
    """Raised when a cycle is detected in the job dependency graph."""


@dataclass
class DependencyGraph:
    """Directed acyclic graph of job dependencies."""

    _deps: Dict[str, Set[str]] = field(default_factory=dict)

    @classmethod
    def from_jobs(cls, jobs: Iterable[JobConfig]) -> "DependencyGraph":
        graph = cls()
        for job in jobs:
            depends_on: List[str] = getattr(job, "depends_on", None) or []
            graph._deps[job.name] = set(depends_on)
        return graph

    def dependencies_of(self, name: str) -> Set[str]:
        """Return the direct dependencies of *name*."""
        return set(self._deps.get(name, set()))

    def topological_order(self) -> List[str]:
        """Return job names in a valid execution order (dependencies first).

        Raises DependencyCycleError if a cycle is detected.
        """
        visited: Set[str] = set()
        in_stack: Set[str] = set()
        order: List[str] = []

        def visit(node: str) -> None:
            if node in in_stack:
                raise DependencyCycleError(
                    f"Dependency cycle detected involving job '{node}'"
                )
            if node in visited:
                return
            in_stack.add(node)
            for dep in self._deps.get(node, set()):
                visit(dep)
            in_stack.discard(node)
            visited.add(node)
            order.append(node)

        for name in self._deps:
            visit(name)

        return order

    def ready_to_run(self, completed: Set[str]) -> List[str]:
        """Return jobs whose dependencies have all completed successfully."""
        result = []
        for name, deps in self._deps.items():
            if name not in completed and deps.issubset(completed):
                result.append(name)
        return result
