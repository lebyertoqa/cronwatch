"""Entry point for the cronwatch daemon."""

from __future__ import annotations

import logging
import signal
import sys
import time
from pathlib import Path
from typing import Optional

from cronwatch.alerting import Alerter, EmailAlerter
from cronwatch.config import AlertConfig, CronwatchConfig, load_config
from cronwatch.executor import run_job
from cronwatch.history import HistoryStore
from cronwatch.scheduler import Scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("cronwatch")

_TICK_INTERVAL = 30  # seconds


def _build_alerter(cfg: AlertConfig) -> Optional[Alerter]:
    if cfg.email:
        return EmailAlerter(cfg)
    return None


def main(config_path: str = "/etc/cronwatch/config.yaml") -> None:
    cfg: CronwatchConfig = load_config(config_path)
    alerter = _build_alerter(cfg.alert)
    history_path = Path(cfg.history_path) if hasattr(cfg, "history_path") and cfg.history_path else None
    store = HistoryStore(path=history_path) if history_path else HistoryStore()
    scheduler = Scheduler(cfg.jobs)

    running = True

    def _stop(signum, frame):  # noqa: ANN001
        nonlocal running
        log.info("Received signal %s, shutting down", signum)
        running = False

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    log.info("cronwatch started, monitoring %d job(s)", len(cfg.jobs))

    while running:
        due_jobs = scheduler.tick()
        for job in due_jobs:
            log.info("Running job: %s", job.name)
            result = run_job(job)
            store.record(result)
            if result.succeeded:
                log.info("Job %s succeeded in %.2fs", job.name, result.duration_seconds)
            else:
                log.error(
                    "Job %s failed (exit %s) in %.2fs",
                    job.name,
                    result.exit_code,
                    result.duration_seconds,
                )
                if alerter:
                    alerter.send(result)
        time.sleep(_TICK_INTERVAL)

    log.info("cronwatch stopped")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/etc/cronwatch/config.yaml")
