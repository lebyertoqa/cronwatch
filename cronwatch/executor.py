import subprocess
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

from cronwatch.config import JobConfig

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    job_name: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    started_at: float
    finished_at: float
    timed_out: bool = False
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out and self.error is None


def run_job(job: JobConfig) -> ExecutionResult:
    """Execute a cron job and return its result."""
    logger.info("Running job '%s': %s", job.name, job.command)
    started_at = time.time()
    timed_out = False
    error: Optional[str] = None

    try:
        proc = subprocess.run(
            job.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=job.timeout_seconds,
        )
        exit_code = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = -1
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        error = f"Job timed out after {job.timeout_seconds}s"
        logger.warning("Job '%s' timed out after %ss", job.name, job.timeout_seconds)
    except Exception as exc:  # noqa: BLE001
        exit_code = -1
        stdout = ""
        stderr = ""
        error = str(exc)
        logger.exception("Unexpected error running job '%s'", job.name)

    finished_at = time.time()
    duration = finished_at - started_at

    result = ExecutionResult(
        job_name=job.name,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=round(duration, 3),
        started_at=started_at,
        finished_at=finished_at,
        timed_out=timed_out,
        error=error,
    )

    if result.success:
        logger.info("Job '%s' succeeded in %.3fs", job.name, duration)
    else:
        logger.error(
            "Job '%s' failed (exit_code=%d, timed_out=%s) in %.3fs",
            job.name,
            exit_code,
            timed_out,
            duration,
        )

    return result
