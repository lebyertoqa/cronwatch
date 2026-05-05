"""Configuration loader for cronwatch."""

import os
import yaml
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class JobConfig:
    name: str
    schedule: str
    command: str
    timeout: int = 3600
    alert_on_failure: bool = True
    alert_on_timeout: bool = True
    notify: List[str] = field(default_factory=list)


@dataclass
class AlertConfig:
    email: Optional[str] = None
    webhook_url: Optional[str] = None
    smtp_host: str = "localhost"
    smtp_port: int = 25
    smtp_from: str = "cronwatch@localhost"


@dataclass
class CronwatchConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    alert: AlertConfig = field(default_factory=AlertConfig)
    log_file: str = "/var/log/cronwatch.log"
    state_dir: str = "/var/lib/cronwatch"
    check_interval: int = 60


def load_config(path: str) -> CronwatchConfig:
    """Load and parse a YAML configuration file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as f:
        raw = yaml.safe_load(f) or {}

    alert_raw = raw.get("alert", {})
    alert = AlertConfig(
        email=alert_raw.get("email"),
        webhook_url=alert_raw.get("webhook_url"),
        smtp_host=alert_raw.get("smtp_host", "localhost"),
        smtp_port=alert_raw.get("smtp_port", 25),
        smtp_from=alert_raw.get("smtp_from", "cronwatch@localhost"),
    )

    jobs = [
        JobConfig(
            name=j["name"],
            schedule=j["schedule"],
            command=j["command"],
            timeout=j.get("timeout", 3600),
            alert_on_failure=j.get("alert_on_failure", True),
            alert_on_timeout=j.get("alert_on_timeout", True),
            notify=j.get("notify", []),
        )
        for j in raw.get("jobs", [])
    ]

    return CronwatchConfig(
        jobs=jobs,
        alert=alert,
        log_file=raw.get("log_file", "/var/log/cronwatch.log"),
        state_dir=raw.get("state_dir", "/var/lib/cronwatch"),
        check_interval=raw.get("check_interval", 60),
    )
