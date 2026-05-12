"""Tests for cronwatch.job_secrets."""
from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any, Dict, Optional

import pytest

from cronwatch.job_secrets import (
    SecretRef,
    missing_secrets,
    redacted_secrets,
    resolve_secrets,
    secrets_for,
)


def _job(secrets: Optional[Dict[str, Any]] = None) -> SimpleNamespace:
    return SimpleNamespace(secrets=secrets)


# ---------------------------------------------------------------------------
# SecretRef
# ---------------------------------------------------------------------------

def test_secret_ref_resolves_from_env(monkeypatch):
    monkeypatch.setenv("MY_SECRET", "hunter2")
    ref = SecretRef(env_var="MY_SECRET")
    assert ref.resolve() == "hunter2"


def test_secret_ref_falls_back_to_default(monkeypatch):
    monkeypatch.delenv("MISSING_VAR", raising=False)
    ref = SecretRef(env_var="MISSING_VAR", default="fallback")
    assert ref.resolve() == "fallback"


def test_secret_ref_returns_none_when_absent(monkeypatch):
    monkeypatch.delenv("MISSING_VAR", raising=False)
    ref = SecretRef(env_var="MISSING_VAR")
    assert ref.resolve() is None


def test_secret_ref_is_available_when_env_set(monkeypatch):
    monkeypatch.setenv("MY_SECRET", "x")
    assert SecretRef(env_var="MY_SECRET").is_available() is True


def test_secret_ref_is_available_when_default_set(monkeypatch):
    monkeypatch.delenv("MISSING_VAR", raising=False)
    assert SecretRef(env_var="MISSING_VAR", default="d").is_available() is True


def test_secret_ref_not_available_when_absent(monkeypatch):
    monkeypatch.delenv("MISSING_VAR", raising=False)
    assert SecretRef(env_var="MISSING_VAR").is_available() is False


# ---------------------------------------------------------------------------
# secrets_for
# ---------------------------------------------------------------------------

def test_secrets_for_returns_empty_when_none():
    assert secrets_for(_job(None)) == {}


def test_secrets_for_returns_empty_when_empty_dict():
    assert secrets_for(_job({})) == {}


def test_secrets_for_parses_dict_spec():
    job = _job({"DB_PASS": {"env_var": "DB_PASSWORD", "default": "secret"}})
    refs = secrets_for(job)
    assert "DB_PASS" in refs
    assert refs["DB_PASS"].env_var == "DB_PASSWORD"
    assert refs["DB_PASS"].default == "secret"


def test_secrets_for_parses_string_spec():
    job = _job({"API_KEY": "API_KEY_ENV"})
    refs = secrets_for(job)
    assert refs["API_KEY"].env_var == "API_KEY_ENV"
    assert refs["API_KEY"].default is None


# ---------------------------------------------------------------------------
# resolve_secrets
# ---------------------------------------------------------------------------

def test_resolve_secrets_returns_resolved_values(monkeypatch):
    monkeypatch.setenv("DB_PASSWORD", "s3cr3t")
    job = _job({"db_pass": "DB_PASSWORD"})
    assert resolve_secrets(job) == {"db_pass": "s3cr3t"}


def test_resolve_secrets_omits_missing(monkeypatch):
    monkeypatch.delenv("MISSING", raising=False)
    job = _job({"key": "MISSING"})
    assert resolve_secrets(job) == {}


# ---------------------------------------------------------------------------
# missing_secrets / redacted_secrets
# ---------------------------------------------------------------------------

def test_missing_secrets_lists_unresolvable(monkeypatch):
    monkeypatch.delenv("GONE", raising=False)
    monkeypatch.setenv("PRESENT", "yes")
    job = _job({"a": "GONE", "b": "PRESENT"})
    assert missing_secrets(job) == ["a"]


def test_redacted_secrets_masks_all_values(monkeypatch):
    monkeypatch.setenv("S1", "real_value")
    job = _job({"token": "S1", "key": {"env_var": "S2", "default": "d"}})
    redacted = redacted_secrets(job)
    assert set(redacted.keys()) == {"token", "key"}
    assert all(v == "***" for v in redacted.values())
