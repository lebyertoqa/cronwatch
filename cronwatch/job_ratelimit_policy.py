"""Per-job rate limit policy: maximum alert count within a rolling window."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class RateLimitRule:
    max_alerts: int
    window_seconds: int


@dataclass
class JobRateLimitPolicy:
    """Holds per-job and default rate-limit rules."""

    default_max_alerts: int = 5
    default_window_seconds: int = 3600
    per_job: Dict[str, RateLimitRule] = field(default_factory=dict)

    def rule_for(self, job_name: str) -> RateLimitRule:
        """Return the rate-limit rule for *job_name*, falling back to defaults."""
        if job_name in self.per_job:
            return self.per_job[job_name]
        return RateLimitRule(
            max_alerts=self.default_max_alerts,
            window_seconds=self.default_window_seconds,
        )

    def max_alerts_for(self, job_name: str) -> int:
        return self.rule_for(job_name).max_alerts

    def window_seconds_for(self, job_name: str) -> int:
        return self.rule_for(job_name).window_seconds


def build_policy(
    default_max_alerts: int = 5,
    default_window_seconds: int = 3600,
    per_job: Optional[Dict[str, Dict]] = None,
) -> JobRateLimitPolicy:
    """Construct a :class:`JobRateLimitPolicy` from plain dicts (e.g. parsed YAML)."""
    rules: Dict[str, RateLimitRule] = {}
    for name, cfg in (per_job or {}).items():
        rules[name] = RateLimitRule(
            max_alerts=cfg.get("max_alerts", default_max_alerts),
            window_seconds=cfg.get("window_seconds", default_window_seconds),
        )
    return JobRateLimitPolicy(
        default_max_alerts=default_max_alerts,
        default_window_seconds=default_window_seconds,
        per_job=rules,
    )
