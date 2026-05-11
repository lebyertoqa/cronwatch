"""Pre- and post-execution hooks for cron jobs."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

from cronwatch.config import JobConfig
from cronwatch.executor import ExecutionResult


@dataclass
class HookResult:
    hook_cmd: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.returncode == 0


def _run_hook(cmd: str, timeout: int = 30) -> HookResult:
    """Run a single shell hook command and return its result."""
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return HookResult(
            hook_cmd=cmd,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
    except subprocess.TimeoutExpired:
        return HookResult(hook_cmd=cmd, returncode=-1, stdout="", stderr="hook timed out")


@dataclass
class HookPolicy:
    """Resolves which hooks to run for a given job."""
    global_pre: List[str] = field(default_factory=list)
    global_post: List[str] = field(default_factory=list)
    hook_timeout: int = 30

    def pre_hooks(self, job: JobConfig) -> List[str]:
        job_pre: List[str] = getattr(job, "pre_hooks", None) or []
        return self.global_pre + job_pre

    def post_hooks(self, job: JobConfig) -> List[str]:
        job_post: List[str] = getattr(job, "post_hooks", None) or []
        return self.global_post + job_post


def run_pre_hooks(policy: HookPolicy, job: JobConfig) -> List[HookResult]:
    """Execute all pre-hooks for *job*; return results in order."""
    return [_run_hook(cmd, policy.hook_timeout) for cmd in policy.pre_hooks(job)]


def run_post_hooks(
    policy: HookPolicy,
    job: JobConfig,
    result: Optional[ExecutionResult] = None,
) -> List[HookResult]:
    """Execute all post-hooks for *job*; return results in order."""
    return [_run_hook(cmd, policy.hook_timeout) for cmd in policy.post_hooks(job)]
