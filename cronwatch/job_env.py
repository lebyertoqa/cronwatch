"""Utilities for managing per-job environment variable injection."""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from cronwatch.config import JobConfig


def env_for(job: JobConfig) -> Dict[str, str]:
    """Return the environment variables defined for *job*.

    Returns an empty dict when the job has no ``env`` attribute or it is
    ``None``.
    """
    raw = getattr(job, "env", None)
    if not raw:
        return {}
    return dict(raw)


def merged_env(job: JobConfig, base: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Return a copy of *base* (defaults to the current process environment)
    with the job-specific variables overlaid.

    Job-level variables take precedence over *base*.
    """
    if base is None:
        base = dict(os.environ)
    result = dict(base)
    result.update(env_for(job))
    return result


def missing_required(job: JobConfig, required_keys: List[str]) -> List[str]:
    """Return the subset of *required_keys* that are absent from the job env."""
    job_env = env_for(job)
    return [k for k in required_keys if k not in job_env]


def redacted_env(job: JobConfig, secret_keys: Optional[List[str]] = None) -> Dict[str, str]:
    """Return the job environment with values for *secret_keys* replaced by
    ``'***'``.  Useful for safe logging.
    """
    secrets = set(secret_keys or [])
    return {
        k: ("***" if k in secrets else v)
        for k, v in env_for(job).items()
    }
