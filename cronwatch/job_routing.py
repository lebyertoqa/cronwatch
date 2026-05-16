"""Route jobs to specific alerter channels based on tags, labels, or metadata."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwatch.alerting import Alerter


@dataclass
class RoutingRule:
    """A single routing rule mapping a selector to an alerter channel name."""
    channel: str
    tag: Optional[str] = None
    label_key: Optional[str] = None
    label_value: Optional[str] = None
    job_name: Optional[str] = None

    def matches(self, job) -> bool:
        """Return True if this rule applies to *job*."""
        if self.job_name is not None:
            return getattr(job, "name", None) == self.job_name
        if self.tag is not None:
            tags = set(getattr(job, "tags", None) or [])
            return self.tag in tags
        if self.label_key is not None:
            labels: Dict[str, str] = dict(getattr(job, "labels", None) or {})
            if self.label_key not in labels:
                return False
            if self.label_value is not None:
                return labels[self.label_key] == self.label_value
            return True
        return False


@dataclass
class JobRouter:
    """Routes a job to one or more alerter channels.

    Rules are evaluated in order; all matching rules contribute their channel.
    If no rule matches, *default_channel* is used.
    """
    rules: List[RoutingRule] = field(default_factory=list)
    default_channel: str = "default"
    channels: Dict[str, Alerter] = field(default_factory=dict)

    def channels_for(self, job) -> List[str]:
        """Return the list of channel names that should receive alerts for *job*."""
        matched = [r.channel for r in self.rules if r.matches(job)]
        return matched if matched else [self.default_channel]

    def alerters_for(self, job) -> List[Alerter]:
        """Return the Alerter instances resolved for *job*."""
        result: List[Alerter] = []
        for name in self.channels_for(job):
            alerter = self.channels.get(name)
            if alerter is not None:
                result.append(alerter)
        return result


def build_router(
    rules_cfg: List[Dict],
    channels: Dict[str, Alerter],
    default_channel: str = "default",
) -> JobRouter:
    """Construct a :class:`JobRouter` from plain-dict configuration.

    Each entry in *rules_cfg* may contain: ``channel``, ``tag``,
    ``label_key``, ``label_value``, ``job_name``.
    """
    rules = [
        RoutingRule(
            channel=r["channel"],
            tag=r.get("tag"),
            label_key=r.get("label_key"),
            label_value=r.get("label_value"),
            job_name=r.get("job_name"),
        )
        for r in rules_cfg
    ]
    return JobRouter(rules=rules, default_channel=default_channel, channels=channels)
