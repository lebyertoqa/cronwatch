"""Backoff strategy calculations for retried cron jobs."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class BackoffStrategy:
    """Describes how delay grows between retry attempts."""

    base_seconds: float = 5.0
    multiplier: float = 2.0
    max_seconds: float = 300.0
    jitter: bool = False


@dataclass
class BackoffPolicy:
    """Maps job names to their individual backoff strategies."""

    default: BackoffStrategy = field(default_factory=BackoffStrategy)
    per_job: Dict[str, BackoffStrategy] = field(default_factory=dict)

    def strategy_for(self, job_name: str) -> BackoffStrategy:
        """Return the backoff strategy for *job_name*, falling back to default."""
        return self.per_job.get(job_name, self.default)


def delay_seconds(strategy: BackoffStrategy, attempt: int) -> float:
    """Return the delay in seconds before *attempt* (1-based).

    Attempt 1 is the first retry (after the initial failure), so the delay
    before it uses ``base_seconds * multiplier^0 == base_seconds``.
    """
    if attempt < 1:
        raise ValueError(f"attempt must be >= 1, got {attempt}")
    raw = strategy.base_seconds * math.pow(strategy.multiplier, attempt - 1)
    return min(raw, strategy.max_seconds)


def delays_for(strategy: BackoffStrategy, total_attempts: int) -> list[float]:
    """Return a list of delays for each retry attempt up to *total_attempts*."""
    return [delay_seconds(strategy, i) for i in range(1, total_attempts + 1)]


def build_backoff_policy(
    default_base: float = 5.0,
    default_multiplier: float = 2.0,
    default_max: float = 300.0,
    per_job: Optional[Dict[str, Dict]] = None,
) -> BackoffPolicy:
    """Convenience constructor used by the application bootstrap."""
    default = BackoffStrategy(
        base_seconds=default_base,
        multiplier=default_multiplier,
        max_seconds=default_max,
    )
    job_strategies: Dict[str, BackoffStrategy] = {}
    for name, cfg in (per_job or {}).items():
        job_strategies[name] = BackoffStrategy(
            base_seconds=cfg.get("base_seconds", default_base),
            multiplier=cfg.get("multiplier", default_multiplier),
            max_seconds=cfg.get("max_seconds", default_max),
        )
    return BackoffPolicy(default=default, per_job=job_strategies)
