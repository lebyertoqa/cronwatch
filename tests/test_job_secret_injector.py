"""Tests for cronwatch.job_secret_injector."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, Optional

import pytest

from cronwatch.job_secret_injector import (
    SecretInjectionError,
    inject_secrets,
    safe_inject_secrets,
)


def _job(name: str = "myjob", secrets: Optional[Dict[str, Any]] = None):
    return SimpleNamespace(name=name, secrets=secrets)


# ---------------------------------------------------------------------------
# inject_secrets
# ---------------------------------------------------------------------------

def test_inject_merges_resolved_secret(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "tok123")
    job = _job(secrets={"API_TOKEN": "API_TOKEN"})
    result = inject_secrets(job, {"PATH": "/usr/bin"})
    assert result["API_TOKEN"] == "tok123"
    assert result["PATH"] == "/usr/bin"


def test_inject_raises_when_secret_missing(monkeypatch):
    monkeypatch.delenv("MISSING_SECRET", raising=False)
    job = _job(secrets={"key": "MISSING_SECRET"})
    with pytest.raises(SecretInjectionError) as exc_info:
        inject_secrets(job, {})
    assert "myjob" in str(exc_info.value)
    assert "key" in str(exc_info.value)


def test_inject_error_stores_missing_names(monkeypatch):
    monkeypatch.delenv("A", raising=False)
    monkeypatch.delenv("B", raising=False)
    job = _job(secrets={"x": "A", "y": "B"})
    with pytest.raises(SecretInjectionError) as exc_info:
        inject_secrets(job, {})
    assert set(exc_info.value.missing) == {"x", "y"}


def test_inject_no_secrets_returns_base_env():
    job = _job(secrets=None)
    base = {"HOME": "/root"}
    result = inject_secrets(job, base)
    assert result == base


def test_inject_secret_overrides_base_env(monkeypatch):
    monkeypatch.setenv("DB_PASS", "new_pass")
    job = _job(secrets={"DB_PASS": "DB_PASS"})
    result = inject_secrets(job, {"DB_PASS": "old_pass"})
    assert result["DB_PASS"] == "new_pass"


# ---------------------------------------------------------------------------
# safe_inject_secrets
# ---------------------------------------------------------------------------

def test_safe_inject_returns_empty_missing_when_all_resolved(monkeypatch):
    monkeypatch.setenv("TOKEN", "abc")
    job = _job(secrets={"TOKEN": "TOKEN"})
    env, missing = safe_inject_secrets(job, {})
    assert env["TOKEN"] == "abc"
    assert missing == []


def test_safe_inject_returns_missing_names_without_raising(monkeypatch):
    monkeypatch.delenv("GONE", raising=False)
    monkeypatch.setenv("PRESENT", "yes")
    job = _job(secrets={"gone_key": "GONE", "present_key": "PRESENT"})
    env, missing = safe_inject_secrets(job, {})
    assert missing == ["gone_key"]
    assert env["present_key"] == "yes"
    assert "gone_key" not in env


def test_safe_inject_preserves_base_env(monkeypatch):
    monkeypatch.delenv("NOPE", raising=False)
    job = _job(secrets={"k": "NOPE"})
    env, _ = safe_inject_secrets(job, {"EXISTING": "value"})
    assert env["EXISTING"] == "value"


def test_safe_inject_no_secrets_returns_base_unchanged():
    job = _job(secrets={})
    base = {"X": "1"}
    env, missing = safe_inject_secrets(job, base)
    assert env == base
    assert missing == []
