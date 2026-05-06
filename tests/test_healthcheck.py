"""Tests for cronwatch.healthcheck."""

from __future__ import annotations

import json
import socket
import time

import pytest

from cronwatch.healthcheck import HealthCheckServer


def _free_port() -> int:
    """Return an ephemeral port that is currently free."""
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _get(port: int, path: str = "/health") -> tuple[int, dict]:
    """Perform a plain HTTP GET and return (status_code, json_body)."""
    import http.client

    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path)
    resp = conn.getresponse()
    body = json.loads(resp.read())
    conn.close()
    return resp.status, body


@pytest.fixture()
def healthy_server():
    port = _free_port()
    srv = HealthCheckServer(port=port, status_fn=lambda: {"healthy": True, "jobs": []})
    srv.start()
    time.sleep(0.05)  # give the thread a moment to bind
    yield port, srv
    srv.stop()


@pytest.fixture()
def unhealthy_server():
    port = _free_port()
    srv = HealthCheckServer(
        port=port, status_fn=lambda: {"healthy": False, "reason": "last job failed"}
    )
    srv.start()
    time.sleep(0.05)
    yield port, srv
    srv.stop()


def test_healthy_returns_200(healthy_server):
    port, _ = healthy_server
    status, body = _get(port)
    assert status == 200
    assert body["healthy"] is True


def test_unhealthy_returns_503(unhealthy_server):
    port, _ = unhealthy_server
    status, body = _get(port)
    assert status == 503
    assert body["healthy"] is False


def test_root_path_also_works(healthy_server):
    port, _ = healthy_server
    status, _ = _get(port, path="/")
    assert status == 200


def test_unknown_path_returns_404(healthy_server):
    port, _ = healthy_server
    import http.client

    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", "/unknown")
    resp = conn.getresponse()
    assert resp.status == 404
    conn.close()


def test_status_fn_called_on_each_request():
    port = _free_port()
    calls: list[int] = []

    def _status() -> dict:
        calls.append(1)
        return {"healthy": True}

    srv = HealthCheckServer(port=port, status_fn=_status)
    srv.start()
    time.sleep(0.05)
    try:
        _get(port)
        _get(port)
        assert len(calls) == 2
    finally:
        srv.stop()
