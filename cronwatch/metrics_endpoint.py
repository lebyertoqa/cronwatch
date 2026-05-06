"""HTTP endpoint that exposes MetricsCollector data as JSON."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Optional

from cronwatch.metrics import MetricsCollector


class _MetricsHandler(BaseHTTPRequestHandler):
    """Minimal request handler – serves /metrics as JSON."""

    collector: MetricsCollector  # injected by MetricsEndpoint

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return

        payload = {
            name: {
                "total_runs": m.total_runs,
                "total_failures": m.total_failures,
                "success_rate": m.success_rate,
                "average_duration_seconds": m.average_duration,
                "last_exit_code": m.last_exit_code,
            }
            for name, m in self.collector.all().items()
        }
        body = json.dumps(payload, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: object) -> None:  # silence default logging
        pass


class MetricsEndpoint:
    """Background HTTP server that exposes job metrics."""

    def __init__(self, collector: MetricsCollector, host: str = "127.0.0.1", port: int = 9091) -> None:
        self._collector = collector
        self._host = host
        self._port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[Thread] = None

    def start(self) -> None:
        """Start the metrics HTTP server in a daemon thread."""

        class Handler(_MetricsHandler):
            collector = self._collector  # type: ignore[assignment]

        self._server = HTTPServer((self._host, self._port), Handler)
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Shut down the server gracefully."""
        if self._server:
            self._server.shutdown()
            self._server = None

    @property
    def address(self) -> str:
        return f"http://{self._host}:{self._port}/metrics"
