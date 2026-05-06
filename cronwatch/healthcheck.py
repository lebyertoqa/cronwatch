"""HTTP health-check endpoint for cronwatch.

Exposes a tiny HTTP server (single-threaded) so external monitoring tools
(e.g. UptimeRobot, Kubernetes liveness probes) can verify the daemon is alive
and inspect the status of recently executed jobs.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable


class _Handler(BaseHTTPRequestHandler):
    """Minimal request handler; status_fn is injected at class creation."""

    status_fn: Callable[[], dict]  # set by HealthCheckServer

    def do_GET(self) -> None:  # noqa: N802
        if self.path not in ("/", "/health"):
            self.send_response(404)
            self.end_headers()
            return

        payload = self.status_fn()
        body = json.dumps(payload).encode()
        healthy = payload.get("healthy", False)
        code = 200 if healthy else 503

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args, **kwargs) -> None:  # noqa: D401
        """Suppress default stderr logging."""


class HealthCheckServer:
    """Background thread that serves a /health endpoint.

    Args:
        port: TCP port to listen on (default 8080).
        status_fn: Callable that returns a dict with at least a
            ``healthy`` boolean key.  Called on every request.
    """

    def __init__(self, port: int, status_fn: Callable[[], dict]) -> None:
        self._port = port
        self._status_fn = status_fn
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the HTTP server in a daemon thread."""
        handler_cls = type(
            "_BoundHandler",
            (_Handler,),
            {"status_fn": staticmethod(self._status_fn)},
        )
        self._server = HTTPServer(("0.0.0.0", self._port), handler_cls)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="cronwatch-healthcheck",
        )
        self._thread.start()

    def stop(self) -> None:
        """Shut down the HTTP server gracefully."""
        if self._server:
            self._server.shutdown()
            self._server = None
