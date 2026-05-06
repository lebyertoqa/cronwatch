"""Tests for MetricsCollector and MetricsEndpoint."""
from __future__ import annotations

import socket
import urllib.request
import json
from datetime import datetime, timezone

import pytest

from cronwatch.executor import ExecutionResult
from cronwatch.metrics import JobMetrics, MetricsCollector
from cronwatch.metrics_endpoint import MetricsEndpoint


def _utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _result(name: str = "backup", success: bool = True, duration: float = 1.0, exit_code: int = 0) -> ExecutionResult:
    return ExecutionResult(
        job_name=name,
        success=success,
        exit_code=exit_code,
        stdout="",
        stderr="",
        duration_seconds=duration,
        started_at=_utc(),
    )


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---------------------------------------------------------------------------
# MetricsCollector unit tests
# ---------------------------------------------------------------------------

def test_initial_get_returns_none():
    c = MetricsCollector()
    assert c.get("unknown") is None


def test_record_increments_total_runs():
    c = MetricsCollector()
    c.record(_result())
    c.record(_result())
    assert c.get("backup").total_runs == 2


def test_failure_increments_total_failures():
    c = MetricsCollector()
    c.record(_result(success=False, exit_code=1))
    m = c.get("backup")
    assert m.total_failures == 1


def test_success_rate_all_successes():
    c = MetricsCollector()
    for _ in range(4):
        c.record(_result())
    assert c.get("backup").success_rate == pytest.approx(1.0)


def test_success_rate_mixed():
    c = MetricsCollector()
    c.record(_result(success=True))
    c.record(_result(success=False, exit_code=1))
    assert c.get("backup").success_rate == pytest.approx(0.5)


def test_average_duration():
    c = MetricsCollector()
    c.record(_result(duration=2.0))
    c.record(_result(duration=4.0))
    assert c.get("backup").average_duration == pytest.approx(3.0)


def test_all_returns_all_jobs():
    c = MetricsCollector()
    c.record(_result(name="job_a"))
    c.record(_result(name="job_b"))
    assert set(c.all().keys()) == {"job_a", "job_b"}


def test_reset_single_job():
    c = MetricsCollector()
    c.record(_result(name="job_a"))
    c.record(_result(name="job_b"))
    c.reset("job_a")
    assert c.get("job_a") is None
    assert c.get("job_b") is not None


def test_reset_all():
    c = MetricsCollector()
    c.record(_result())
    c.reset()
    assert c.all() == {}


# ---------------------------------------------------------------------------
# MetricsEndpoint integration tests
# ---------------------------------------------------------------------------

def test_metrics_endpoint_returns_json():
    port = _free_port()
    collector = MetricsCollector()
    collector.record(_result(name="sync", success=True, duration=0.5))
    endpoint = MetricsEndpoint(collector, port=port)
    endpoint.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics") as resp:
            assert resp.status == 200
            data = json.loads(resp.read())
        assert "sync" in data
        assert data["sync"]["total_runs"] == 1
    finally:
        endpoint.stop()


def test_metrics_endpoint_404_for_unknown_path():
    port = _free_port()
    endpoint = MetricsEndpoint(MetricsCollector(), port=port)
    endpoint.start()
    try:
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/unknown")
        assert exc_info.value.code == 404
    finally:
        endpoint.stop()
