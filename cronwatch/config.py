"""Configuration models and loader for cronwatch."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class JobConfig:
    name: str
    command: str
    schedule: str
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    timeout_seconds: int = 0
    notify_on_recovery: bool = True


@dataclass
class AlertConfig:
    email: List[str] = field(default_factory=list)
    smtp_host: str = "localhost"
    smtp_port: int = 25
    from_address: str = "cronwatch@localhost"
    max_alerts_per_hour: int = 0


@dataclass
class CronwatchConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    alert: AlertConfig = field(default_factory=AlertConfig)
    history_path: str = "/var/lib/cronwatch/history.json"
    audit_path: str = "/var/lib/cronwatch/audit.log"
    digest_interval_hours: int = 24
    retention_days: int = 30
    healthcheck_port: int = 8080
    metrics_port: int = 9090


def _parse_job(raw: Dict[str, Any]) -> JobConfig:
    return JobConfig(
        name=raw["name"],
        command=raw["command"],
        schedule=raw["schedule"],
        tags=raw.get("tags") or [],
        enabled=raw.get("enabled", True),
        timeout_seconds=raw.get("timeout_seconds", 0),
        notify_on_recovery=raw.get("notify_on_recovery", True),
    )


def _parse_alert(raw: Dict[str, Any]) -> AlertConfig:
    return AlertConfig(
        email=raw.get("email") or [],
        smtp_host=raw.get("smtp_host", "localhost"),
        smtp_port=raw.get("smtp_port", 25),
        from_address=raw.get("from_address", "cronwatch@localhost"),
        max_alerts_per_hour=raw.get("max_alerts_per_hour", 0),
    )


def load_config(path: str | Path) -> CronwatchConfig:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with p.open() as fh:
        raw = yaml.safe_load(fh) or {}

    jobs = [_parse_job(j) for j in raw.get("jobs", [])]
    alert = _parse_alert(raw.get("alert") or {})

    return CronwatchConfig(
        jobs=jobs,
        alert=alert,
        history_path=raw.get("history_path", "/var/lib/cronwatch/history.json"),
        audit_path=raw.get("audit_path", "/var/lib/cronwatch/audit.log"),
        digest_interval_hours=raw.get("digest_interval_hours", 24),
        retention_days=raw.get("retention_days", 30),
        healthcheck_port=raw.get("healthcheck_port", 8080),
        metrics_port=raw.get("metrics_port", 9090),
    )
