"""Orchestrates the full per-job run pipeline: schedule → run → notify → history."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from cronwatch.config import CronwatchConfig
from cronwatch.history import HistoryStore
from cronwatch.job_runner import JobRunner
from cronwatch.notifier import Notifier
from cronwatch.scheduler import Scheduler
from cronwatch.circuit_breaker import CircuitBreaker
from cronwatch.alerting import Alerter

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    job_name: str
    ran: bool
    success: Optional[bool]
    notified: bool
    skipped: bool
    skip_reason: str = ""


class RunPipeline:
    """Drives a single scheduler tick: checks due jobs, runs them, records history."""

    def __init__(
        self,
        config: CronwatchConfig,
        scheduler: Scheduler,
        runner: JobRunner,
        history: HistoryStore,
        notifier: Notifier,
        alerter: Alerter,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self._config = config
        self._scheduler = scheduler
        self._runner = runner
        self._history = history
        self._notifier = notifier
        self._alerter = alerter
        self._circuit_breaker = circuit_breaker

    def tick(self) -> List[PipelineResult]:
        outcomes: List[PipelineResult] = []
        for job in self._config.jobs:
            if not self._scheduler.is_due(job):
                continue
            if self._circuit_breaker and self._circuit_breaker.is_open(job.name):
                logger.warning("Circuit open for %r — skipping.", job.name)
                outcomes.append(
                    PipelineResult(
                        job_name=job.name,
                        ran=False,
                        success=None,
                        notified=False,
                        skipped=True,
                        skip_reason="circuit open",
                    )
                )
                continue

            runner_result = self._runner.run(job)

            if runner_result.skipped:
                outcomes.append(
                    PipelineResult(
                        job_name=job.name,
                        ran=False,
                        success=None,
                        notified=False,
                        skipped=True,
                        skip_reason=runner_result.skip_reason,
                    )
                )
                continue

            result = runner_result.result
            self._history.record(result)

            if self._circuit_breaker:
                self._circuit_breaker.record(job.name, result.success)

            notified = False
            if self._notifier.should_notify(result):
                self._alerter.send(result)
                notified = True

            outcomes.append(
                PipelineResult(
                    job_name=job.name,
                    ran=True,
                    success=result.success,
                    notified=notified,
                    skipped=False,
                )
            )
        return outcomes
