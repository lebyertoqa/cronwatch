"""Scheduler that reads cron job configs and dispatches execution."""

import logging
import time
from datetime import datetime, timezone

from croniter import croniter

from cronwatch.alerting import Alerter
from cronwatch.config import CronwatchConfig, JobConfig
from cronwatch.executor import ExecutionResult, run_job

logger = logging.getLogger(__name__)


def next_run(schedule: str, now: datetime | None = None) -> datetime:
    """Return the next scheduled datetime for a cron expression."""
    if now is None:
        now = datetime.now(tz=timezone.utc)
    it = croniter(schedule, now)
    return it.get_next(datetime)


def is_due(schedule: str, now: datetime | None = None, tolerance_seconds: int = 30) -> bool:
    """Return True if the job is due to run within *tolerance_seconds* of *now*."""
    if now is None:
        now = datetime.now(tz=timezone.utc)
    prev = croniter(schedule, now).get_prev(datetime)
    delta = abs((now - prev).total_seconds())
    return delta <= tolerance_seconds


class Scheduler:
    """Polls job schedules and triggers execution + alerting."""

    def __init__(self, config: CronwatchConfig, alerter: Alerter) -> None:
        self.config = config
        self.alerter = alerter
        self._last_run: dict[str, datetime] = {}

    def tick(self, now: datetime | None = None) -> list[ExecutionResult]:
        """Check all jobs and run any that are due. Returns results for this tick."""
        if now is None:
            now = datetime.now(tz=timezone.utc)
        results: list[ExecutionResult] = []
        for job in self.config.jobs:
            if self._should_run(job, now):
                logger.info("Running job '%s'", job.name)
                result = run_job(job)
                self._last_run[job.name] = now
                results.append(result)
                if not result.success:
                    logger.warning("Job '%s' failed — sending alert", job.name)
                    self.alerter.send(result)
        return results

    def _should_run(self, job: JobConfig, now: datetime) -> bool:
        last = self._last_run.get(job.name)
        if last is not None:
            # Avoid double-firing within the same minute
            if (now - last).total_seconds() < 60:
                return False
        return is_due(job.schedule, now)

    def run_forever(self, poll_interval: int = 30) -> None:  # pragma: no cover
        """Block forever, polling every *poll_interval* seconds."""
        logger.info("Scheduler started (poll interval=%ds)", poll_interval)
        while True:
            self.tick()
            time.sleep(poll_interval)
