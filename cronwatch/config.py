"""Configuration loading and dataclasses for cronwatch."""
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
    tags: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 0
    env: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlertConfig:
    email_to: List[str] = field(default_factory=list)
    email_from: str = "cronwatch@localhost"
    smtp_host: str = "localhost"
    smtp_port: int = 25
    smtp_tls: bool = False
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None


@dataclass
class CronwatchConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    alert: AlertConfig = field(default_factory=AlertConfig)
    history_path: str = "/var/lib/cronwatch/history.json"
    audit_path: str = "/var/lib/cronwatch/audit.jsonl"
    lock_dir: str = "/var/run/cronwatch"
    healthcheck_port: int = 0
    metrics_port: int = 0
    digest_interval_hours: int = 24
    notification_interval_seconds: int = 3600
    max_alerts_per_window: int = 10
    alert_window_seconds: int = 3600


def _parse_job(raw: Dict[str, Any]) -> JobConfig:
    return JobConfig(
        name=raw["name"],
        command=raw["command"],
        schedule=raw["schedule"],
        enabled=raw.get("enabled", True),
        tags=raw.get("tags") or [],
        labels=raw.get("labels") or {},
        timeout_seconds=raw.get("timeout_seconds", 0),
        env=raw.get("env") or {},
    )


def _parse_alert(raw: Dict[str, Any]) -> AlertConfig:
    return AlertConfig(
        email_to=raw.get("email_to") or [],
        email_from=raw.get("email_from", "cronwatch@localhost"),
        smtp_host=raw.get("smtp_host", "localhost"),
        smtp_port=raw.get("smtp_port", 25),
        smtp_tls=raw.get("smtp_tls", False),
        smtp_user=raw.get("smtp_user"),
        smtp_password=raw.get("smtp_password"),
    )


def load_config(path: str) -> CronwatchConfig:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r") as fh:
        raw = yaml.safe_load(fh) or {}
    jobs = [_parse_job(j) for j in raw.get("jobs", [])]
    alert = _parse_alert(raw.get("alert") or {})
    return CronwatchConfig(
        jobs=jobs,
        alert=alert,
        history_path=raw.get("history_path", "/var/lib/cronwatch/history.json"),
        audit_path=raw.get("audit_path", "/var/lib/cronwatch/audit.jsonl"),
        lock_dir=raw.get("lock_dir", "/var/run/cronwatch"),
        healthcheck_port=raw.get("healthcheck_port", 0),
        metrics_port=raw.get("metrics_port", 0),
        digest_interval_hours=raw.get("digest_interval_hours", 24),
        notification_interval_seconds=raw.get("notification_interval_seconds", 3600),
        max_alerts_per_window=raw.get("max_alerts_per_window", 10),
        alert_window_seconds=raw.get("alert_window_seconds", 3600),
    )
