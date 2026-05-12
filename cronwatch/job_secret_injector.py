"""Inject resolved secrets into a job's environment before execution."""
from __future__ import annotations

from typing import Dict, List

from cronwatch.job_secrets import missing_secrets, resolve_secrets


class SecretInjectionError(Exception):
    """Raised when required secrets cannot be resolved before a job runs."""

    def __init__(self, job_name: str, missing: List[str]) -> None:
        self.job_name = job_name
        self.missing = missing
        names = ", ".join(missing)
        super().__init__(
            f"Job '{job_name}' is missing required secrets: {names}"
        )


def inject_secrets(job, base_env: Dict[str, str]) -> Dict[str, str]:
    """Return *base_env* merged with the resolved secrets for *job*.

    Raises :class:`SecretInjectionError` if any secret cannot be resolved.
    """
    absent = missing_secrets(job)
    if absent:
        raise SecretInjectionError(
            job_name=getattr(job, "name", "<unknown>"),
            missing=absent,
        )

    resolved = resolve_secrets(job)
    return {**base_env, **resolved}


def safe_inject_secrets(
    job, base_env: Dict[str, str]
) -> tuple[Dict[str, str], List[str]]:
    """Like :func:`inject_secrets` but never raises.

    Returns a tuple of ``(merged_env, missing_names)``.  When secrets are
    missing the returned env contains only the resolvable ones merged into
    *base_env*.
    """
    absent = missing_secrets(job)
    resolved = resolve_secrets(job)
    merged = {**base_env, **resolved}
    return merged, absent


def has_all_secrets(job) -> bool:
    """Return ``True`` if all secrets required by *job* can be resolved.

    This is a convenience predicate for callers that want to check secret
    availability without catching :class:`SecretInjectionError` or
    unpacking the tuple returned by :func:`safe_inject_secrets`.

    Example::

        if not has_all_secrets(job):
            logger.warning("Skipping %s: secrets unavailable", job.name)
            return
    """
    return not missing_secrets(job)
