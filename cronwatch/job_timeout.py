"""Job timeout enforcement — wraps execution with a configurable deadline."""

from __future__ import annotations

import signal
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional


class JobTimeoutError(Exception):
    """Raised when a job exceeds its allowed execution time."""

    def __init__(self, job_name: str, timeout_seconds: int) -> None:
        self.job_name = job_name
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Job '{job_name}' timed out after {timeout_seconds}s"
        )


@dataclass
class TimeoutPolicy:
    """Per-job or global timeout configuration."""

    default_seconds: int = 3600  # 1 hour
    per_job: dict[str, int] | None = None

    def timeout_for(self, job_name: str) -> int:
        """Return the effective timeout for *job_name* in seconds."""
        if self.per_job and job_name in self.per_job:
            return self.per_job[job_name]
        return self.default_seconds


@contextmanager
def enforce_timeout(job_name: str, seconds: int):
    """Context manager that raises JobTimeoutError if the block runs too long.

    Uses SIGALRM on POSIX systems; falls back to a daemon thread timer on
    platforms that do not support it (e.g. Windows).
    """
    if seconds <= 0:
        yield
        return

    if hasattr(signal, "SIGALRM") and threading.current_thread() is threading.main_thread():
        def _handler(signum, frame):  # noqa: ANN001
            raise JobTimeoutError(job_name, seconds)

        old_handler = signal.signal(signal.SIGALRM, _handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        # Thread-based fallback
        timed_out: list[bool] = [False]
        current = threading.current_thread()

        def _trigger() -> None:
            timed_out[0] = True
            # Interrupt the target thread by raising in it (best-effort)
            import ctypes
            ctypes.pythonapi.PyThreadState_SetAsyncExc(
                ctypes.c_ulong(current.ident),  # type: ignore[arg-type]
                ctypes.py_object(JobTimeoutError(job_name, seconds)),
            )

        timer = threading.Timer(seconds, _trigger)
        timer.daemon = True
        timer.start()
        try:
            yield
        finally:
            timer.cancel()
