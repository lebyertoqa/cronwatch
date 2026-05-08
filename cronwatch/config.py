"""Configuration loading and dataclasses for cronwatch.

Extends the existing config to support optional `depends_on` and `tags`
fields on JobConfig, plus `labels` for key/value metadata.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class JobConfig:
    name: str
    command: str
    schedule: str
    enabled: bool = True
    timeout: int = 0  # seconds; 0 means no timeout
    tags: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)


@dataclass
class AlertConfig:
    type: str  # e.g. "email"
    recipients: List[str] = field(default_factory=list)
    smtp_host: str = "localhost"
    smtp_port: int = 25
    sender: str = "cronwatch@localhost"


@dataclass
class CronwatchConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    alert: Optional[AlertConfig] = None
    history_path: str = "/var/lib/cronwatch/history.json"
    audit_path: str = "/var/lib/cronwatch/audit.jsonl"
    healthcheck_port: int = 0
    metrics_port: int = 0
    digest_interval_hours: int = 24
    notify_interval_seconds: int = 3600
    max_alerts_per_window: int = 10
    alert_window_seconds: int = 3600
    lock_dir: str = "/tmp/cronwatch/locks"
    retention_days: int = 30
    retention_max_entries: int = 1000


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_job(raw: Dict[str, Any]) -> JobConfig:
    return JobConfig(
        name=raw["name"],
        command=raw["command"],
        schedule=raw["schedule"],
        enabled=raw.get("enabled", True),
        timeout=raw.get("timeout", 0),
        tags=raw.get("tags") or [],
        labels=raw.get("labels") or {},
        depends_on=raw.get("depends_on") or [],
    )


def _parse_alert(raw: Dict[str, Any]) -> AlertConfig:
    return AlertConfig(
        type=raw["type"],
        recipients=raw.get("recipients") or [],
        smtp_host=raw.get("smtp_host", "localhost"),
        smtp_port=raw.get("smtp_port", 25),
        sender=raw.get("sender", "cronwatch@localhost"),
    )


def load_config(path: str) -> CronwatchConfig:
    """Load and parse a YAML configuration file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as fh:
        raw = yaml.safe_load(fh) or {}

    jobs = [_parse_job(j) for j in raw.get("jobs") or []]
    alert = _parse_alert(raw["alert"]) if "alert" in raw else None

    return CronwatchConfig(
        jobs=jobs,
        alert=alert,
        history_path=raw.get("history_path", "/var/lib/cronwatch/history.json"),
        audit_path=raw.get("audit_path", "/var/lib/cronwatch/audit.jsonl"),
        healthcheck_port=raw.get("healthcheck_port", 0),
        metrics_port=raw.get("metrics_port", 0),
        digest_interval_hours=raw.get("digest_interval_hours", 24),
        notify_interval_seconds=raw.get("notify_interval_seconds", 3600),
        max_alerts_per_window=raw.get("max_alerts_per_window", 10),
        alert_window_seconds=raw.get("alert_window_seconds", 3600),
        lock_dir=raw.get("lock_dir", "/tmp/cronwatch/locks"),
        retention_days=raw.get("retention_days", 30),
        retention_max_entries=raw.get("retention_max_entries", 1000),
    )
