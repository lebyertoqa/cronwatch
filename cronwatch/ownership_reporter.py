"""Report on job ownership coverage and contact gaps."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwatch.config import JobConfig
from cronwatch.job_ownership import (
    OwnerInfo,
    all_teams,
    group_by_team,
    jobs_without_owner,
    owner_for,
)


@dataclass
class OwnershipSummary:
    """Ownership statistics for a set of jobs."""
    total_jobs: int
    owned_jobs: int
    unowned_jobs: int
    teams: List[str]
    jobs_missing_contact: List[str]  # job names with owner but no email/slack
    jobs_without_owner: List[str]    # job names with no ownership at all

    @property
    def coverage_pct(self) -> float:
        """Percentage of jobs that have an owner (0-100)."""
        if self.total_jobs == 0:
            return 100.0
        return round(self.owned_jobs / self.total_jobs * 100, 2)


@dataclass
class OwnershipReport:
    """Full ownership report broken down by team."""
    summary: OwnershipSummary
    by_team: Dict[Optional[str], List[str]]  # team -> sorted job names

    def team_job_count(self, team: str) -> int:
        return len(self.by_team.get(team, []))


def build_ownership_report(jobs: List[JobConfig]) -> OwnershipReport:
    """Build a complete ownership report for *jobs*."""
    unowned = jobs_without_owner(jobs)
    unowned_names = sorted(j.name for j in unowned)

    missing_contact: List[str] = []
    for j in jobs:
        info = owner_for(j)
        if info != OwnerInfo() and not info.has_contact():
            missing_contact.append(j.name)

    owned_count = len(jobs) - len(unowned)

    summary = OwnershipSummary(
        total_jobs=len(jobs),
        owned_jobs=owned_count,
        unowned_jobs=len(unowned),
        teams=all_teams(jobs),
        jobs_missing_contact=sorted(missing_contact),
        jobs_without_owner=unowned_names,
    )

    raw_groups = group_by_team(jobs)
    by_team: Dict[Optional[str], List[str]] = {
        team: sorted(j.name for j in members)
        for team, members in raw_groups.items()
    }

    return OwnershipReport(summary=summary, by_team=by_team)
