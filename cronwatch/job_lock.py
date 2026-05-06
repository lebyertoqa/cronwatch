"""Prevent concurrent execution of the same cron job using file-based locks."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional


class LockAcquisitionError(Exception):
    """Raised when a job lock cannot be acquired."""


class JobLock:
    """File-based lock for a single named job.

    The lock file contains the PID of the process that holds it.
    Stale locks (process no longer running) are automatically cleared.
    """

    def __init__(self, job_name: str, lock_dir: str = "/tmp/cronwatch/locks") -> None:
        self.job_name = job_name
        self._lock_dir = Path(lock_dir)
        self._lock_file = self._lock_dir / f"{job_name}.lock"
        self._held = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def acquire(self) -> None:
        """Acquire the lock or raise LockAcquisitionError."""
        self._lock_dir.mkdir(parents=True, exist_ok=True)
        existing_pid = self._read_pid()
        if existing_pid is not None:
            if _pid_running(existing_pid):
                raise LockAcquisitionError(
                    f"Job '{self.job_name}' is already running (pid {existing_pid})"
                )
            # Stale lock — remove it before continuing
            self._lock_file.unlink(missing_ok=True)

        self._lock_file.write_text(str(os.getpid()))
        self._held = True

    def release(self) -> None:
        """Release the lock if held by this process."""
        if not self._held:
            return
        self._lock_file.unlink(missing_ok=True)
        self._held = False

    @property
    def is_held(self) -> bool:
        return self._held

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "JobLock":
        self.acquire()
        return self

    def __exit__(self, *_: object) -> None:
        self.release()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _read_pid(self) -> Optional[int]:
        try:
            return int(self._lock_file.read_text().strip())
        except (FileNotFoundError, ValueError):
            return None


def _pid_running(pid: int) -> bool:
    """Return True if *pid* refers to a running process."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False
