"""An Alerter that dispatches to per-job channels via a JobRouter."""
from __future__ import annotations

from cronwatch.alerting import Alerter
from cronwatch.executor import ExecutionResult
from cronwatch.job_routing import JobRouter


class RoutingAlerter:
    """Wraps a :class:`~cronwatch.job_routing.JobRouter` and implements the
    :class:`~cronwatch.alerting.Alerter` protocol so it can be used anywhere
    a plain alerter is expected.

    On :meth:`send`, the router resolves the correct channel(s) for the job
    referenced in *result* and forwards the call to each resolved alerter.
    """

    def __init__(self, router: JobRouter, jobs: dict | None = None) -> None:
        """
        Parameters
        ----------
        router:
            A configured :class:`JobRouter`.
        jobs:
            Optional mapping of job name → job object.  When provided the
            router can apply tag/label rules.  If absent, only ``job_name``
            rules work.
        """
        self._router = router
        self._jobs: dict = jobs or {}

    # ------------------------------------------------------------------
    # Alerter protocol
    # ------------------------------------------------------------------

    def send(self, result: ExecutionResult) -> None:
        """Route *result* to the appropriate alerter channel(s)."""
        job = self._jobs.get(result.job_name)
        if job is None:
            # Minimal stand-in so name-based rules still work.
            job = _NameOnlyJob(result.job_name)

        alerters = self._router.alerters_for(job)
        for alerter in alerters:
            alerter.send(result)

    def channel_names_for(self, job_name: str) -> list[str]:
        """Return channel names that would be used for *job_name* (for inspection/testing)."""
        job = self._jobs.get(job_name, _NameOnlyJob(job_name))
        return self._router.channels_for(job)


class _NameOnlyJob:
    """Minimal job stand-in that only exposes a name."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.tags: list = []
        self.labels: dict = {}


def build_routing_alerter(
    router: JobRouter,
    jobs: dict | None = None,
) -> RoutingAlerter:
    """Convenience factory used by the main wiring layer."""
    return RoutingAlerter(router=router, jobs=jobs)
