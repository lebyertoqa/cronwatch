"""Tests for cronwatch.job_hooks."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from cronwatch.job_hooks import (
    HookPolicy,
    HookResult,
    _run_hook,
    run_post_hooks,
    run_pre_hooks,
)


def _job(pre=None, post=None):
    j = MagicMock()
    j.name = "test-job"
    j.pre_hooks = pre
    j.post_hooks = post
    return j


# ---------------------------------------------------------------------------
# HookResult
# ---------------------------------------------------------------------------

def test_hook_result_success_when_returncode_zero():
    r = HookResult(hook_cmd="echo hi", returncode=0, stdout="hi", stderr="")
    assert r.success is True


def test_hook_result_failure_when_nonzero():
    r = HookResult(hook_cmd="false", returncode=1, stdout="", stderr="")
    assert r.success is False


# ---------------------------------------------------------------------------
# _run_hook
# ---------------------------------------------------------------------------

def test_run_hook_success():
    result = _run_hook(f"{sys.executable} -c 'print(\"ok\")'")
    assert result.success
    assert "ok" in result.stdout


def test_run_hook_failure():
    result = _run_hook(f"{sys.executable} -c 'raise SystemExit(2)'")
    assert not result.success
    assert result.returncode == 2


def test_run_hook_timeout_returns_negative_one():
    result = _run_hook(f"{sys.executable} -c 'import time; time.sleep(10)'" , timeout=1)
    assert result.returncode == -1
    assert "timed out" in result.stderr


# ---------------------------------------------------------------------------
# HookPolicy
# ---------------------------------------------------------------------------

def test_policy_merges_global_and_job_pre_hooks():
    policy = HookPolicy(global_pre=["echo global"])
    job = _job(pre=["echo job"])
    assert policy.pre_hooks(job) == ["echo global", "echo job"]


def test_policy_merges_global_and_job_post_hooks():
    policy = HookPolicy(global_post=["echo done"])
    job = _job(post=["echo cleanup"])
    assert policy.post_hooks(job) == ["echo done", "echo cleanup"]


def test_policy_handles_none_job_hooks():
    policy = HookPolicy(global_pre=["echo global"])
    job = _job(pre=None)
    assert policy.pre_hooks(job) == ["echo global"]


def test_policy_handles_missing_attribute():
    policy = HookPolicy(global_post=["echo post"])
    job = MagicMock(spec=["name"])  # no pre_hooks / post_hooks attributes
    assert policy.post_hooks(job) == ["echo post"]


# ---------------------------------------------------------------------------
# run_pre_hooks / run_post_hooks
# ---------------------------------------------------------------------------

def test_run_pre_hooks_returns_results_for_each_hook():
    policy = HookPolicy(global_pre=[f"{sys.executable} -c 'pass'", f"{sys.executable} -c 'pass'"])
    results = run_pre_hooks(policy, _job())
    assert len(results) == 2
    assert all(isinstance(r, HookResult) for r in results)


def test_run_post_hooks_empty_when_no_hooks():
    policy = HookPolicy()
    results = run_post_hooks(policy, _job())
    assert results == []


def test_run_pre_hooks_captures_failure():
    policy = HookPolicy(global_pre=[f"{sys.executable} -c 'raise SystemExit(3)'"])
    results = run_pre_hooks(policy, _job())
    assert len(results) == 1
    assert results[0].returncode == 3
