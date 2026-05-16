"""Job ownership: track which team or user owns each cron job."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwatch.config import JobConfig


@dataclass
class OwnerInfo:
    """Ownership metadata for a job."""
    team: Optional[str] = None
    email: Optional[str] = None
    slack: Optional[str] = None
    extra: Dict[str, str] = field(default_factory=dict)

    def has_contact(self) -> bool:
        """Return True if at least one contact channel is set."""
        return bool(self.email or self.slack)


def owner_for(job: JobConfig) -> OwnerInfo:
    """Extract ownership info from a job's metadata."""
    meta: Dict = getattr(job, "metadata", None) or {}
    ownership: Dict = meta.get("ownership", {}) if isinstance(meta, dict) else {}
    if not isinstance(ownership, dict):
        return OwnerInfo()
    extra = {
        k: v
        for k, v in ownership.items()
        if k not in ("team", "email", "slack")
    }
    return OwnerInfo(
        team=ownership.get("team"),
        email=ownership.get("email"),
        slack=ownership.get("slack"),
        extra=extra,
    )


def jobs_owned_by_team(jobs: List[JobConfig], team: str) -> List[JobConfig]:
    """Return jobs whose ownership team matches *team* (case-insensitive)."""
    return [j for j in jobs if (owner_for(j).team or "").lower() == team.lower()]


def jobs_without_owner(jobs: List[JobConfig]) -> List[JobConfig]:
    """Return jobs that have no ownership metadata at all."""
    return [j for j in jobs if owner_for(j) == OwnerInfo()]


def all_teams(jobs: List[JobConfig]) -> List[str]:
    """Return a sorted, deduplicated list of all team names across *jobs*."""
    teams = {owner_for(j).team for j in jobs if owner_for(j).team}
    return sorted(teams)


def group_by_team(jobs: List[JobConfig]) -> Dict[Optional[str], List[JobConfig]]:
    """Group jobs by their owning team.  Jobs with no team are keyed by None."""
    result: Dict[Optional[str], List[JobConfig]] = {}
    for job in jobs:
        key = owner_for(job).team
        result.setdefault(key, []).append(job)
    return result
