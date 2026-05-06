"""Tests for cronwatch.job_lock."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from cronwatch.job_lock import JobLock, LockAcquisitionError


@pytest.fixture()
def lock_dir(tmp_path: Path) -> str:
    return str(tmp_path / "locks")


@pytest.fixture()
def lock(lock_dir: str) -> JobLock:
    return JobLock("test_job", lock_dir=lock_dir)


# ---------------------------------------------------------------------------
# Acquire / release basics
# ---------------------------------------------------------------------------

def test_acquire_creates_lock_file(lock: JobLock, lock_dir: str) -> None:
    lock.acquire()
    assert (Path(lock_dir) / "test_job.lock").exists()
    lock.release()


def test_lock_file_contains_current_pid(lock: JobLock, lock_dir: str) -> None:
    lock.acquire()
    pid = int((Path(lock_dir) / "test_job.lock").read_text())
    assert pid == os.getpid()
    lock.release()


def test_release_removes_lock_file(lock: JobLock, lock_dir: str) -> None:
    lock.acquire()
    lock.release()
    assert not (Path(lock_dir) / "test_job.lock").exists()


def test_is_held_reflects_state(lock: JobLock) -> None:
    assert not lock.is_held
    lock.acquire()
    assert lock.is_held
    lock.release()
    assert not lock.is_held


# ---------------------------------------------------------------------------
# Concurrent / stale lock behaviour
# ---------------------------------------------------------------------------

def test_acquire_raises_when_live_pid_holds_lock(lock_dir: str) -> None:
    first = JobLock("job_a", lock_dir=lock_dir)
    second = JobLock("job_a", lock_dir=lock_dir)
    first.acquire()
    with pytest.raises(LockAcquisitionError, match="already running"):
        second.acquire()
    first.release()


def test_stale_lock_is_cleared_and_reacquired(lock_dir: str) -> None:
    """A lock file referencing a dead PID should be silently replaced."""
    lock_file = Path(lock_dir) / "stale_job.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text("99999999")  # very unlikely to be a real PID

    jl = JobLock("stale_job", lock_dir=lock_dir)
    # Patch _pid_running so we don't depend on the actual PID being dead
    with patch("cronwatch.job_lock._pid_running", return_value=False):
        jl.acquire()
    assert jl.is_held
    jl.release()


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

def test_context_manager_acquires_and_releases(lock: JobLock, lock_dir: str) -> None:
    with lock:
        assert lock.is_held
        assert (Path(lock_dir) / "test_job.lock").exists()
    assert not lock.is_held
    assert not (Path(lock_dir) / "test_job.lock").exists()


def test_context_manager_releases_on_exception(lock: JobLock) -> None:
    with pytest.raises(RuntimeError):
        with lock:
            raise RuntimeError("boom")
    assert not lock.is_held


# ---------------------------------------------------------------------------
# Double release is safe
# ---------------------------------------------------------------------------

def test_double_release_is_safe(lock: JobLock) -> None:
    lock.acquire()
    lock.release()
    lock.release()  # should not raise
