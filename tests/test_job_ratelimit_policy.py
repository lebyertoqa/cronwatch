"""Tests for cronwatch.job_ratelimit_policy."""
import pytest

from cronwatch.job_ratelimit_policy import (
    JobRateLimitPolicy,
    RateLimitRule,
    build_policy,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _policy(**kwargs) -> JobRateLimitPolicy:
    return build_policy(**kwargs)


# ---------------------------------------------------------------------------
# RateLimitRule
# ---------------------------------------------------------------------------

def test_rule_stores_max_alerts():
    rule = RateLimitRule(max_alerts=3, window_seconds=60)
    assert rule.max_alerts == 3


def test_rule_stores_window_seconds():
    rule = RateLimitRule(max_alerts=3, window_seconds=60)
    assert rule.window_seconds == 60


# ---------------------------------------------------------------------------
# Default policy
# ---------------------------------------------------------------------------

def test_default_max_alerts_for_unknown_job():
    policy = _policy(default_max_alerts=5, default_window_seconds=3600)
    assert policy.max_alerts_for("some-job") == 5


def test_default_window_seconds_for_unknown_job():
    policy = _policy(default_max_alerts=5, default_window_seconds=3600)
    assert policy.window_seconds_for("some-job") == 3600


def test_defaults_when_no_per_job_provided():
    policy = build_policy()
    assert policy.max_alerts_for("backup") == 5
    assert policy.window_seconds_for("backup") == 3600


# ---------------------------------------------------------------------------
# Per-job overrides
# ---------------------------------------------------------------------------

def test_per_job_override_max_alerts():
    policy = _policy(
        default_max_alerts=5,
        per_job={"nightly-backup": {"max_alerts": 2, "window_seconds": 1800}},
    )
    assert policy.max_alerts_for("nightly-backup") == 2


def test_per_job_override_window_seconds():
    policy = _policy(
        default_max_alerts=5,
        per_job={"nightly-backup": {"max_alerts": 2, "window_seconds": 1800}},
    )
    assert policy.window_seconds_for("nightly-backup") == 1800


def test_per_job_falls_back_for_other_jobs():
    policy = _policy(
        default_max_alerts=10,
        default_window_seconds=7200,
        per_job={"special-job": {"max_alerts": 1, "window_seconds": 600}},
    )
    assert policy.max_alerts_for("other-job") == 10
    assert policy.window_seconds_for("other-job") == 7200


def test_per_job_partial_override_uses_default_for_missing_key():
    """If only max_alerts is specified, window_seconds falls back to default."""
    policy = _policy(
        default_max_alerts=5,
        default_window_seconds=3600,
        per_job={"partial-job": {"max_alerts": 3}},
    )
    assert policy.max_alerts_for("partial-job") == 3
    assert policy.window_seconds_for("partial-job") == 3600


# ---------------------------------------------------------------------------
# rule_for returns RateLimitRule
# ---------------------------------------------------------------------------

def test_rule_for_returns_rate_limit_rule_instance():
    policy = _policy(default_max_alerts=4, default_window_seconds=900)
    rule = policy.rule_for("any-job")
    assert isinstance(rule, RateLimitRule)


def test_rule_for_per_job_returns_correct_rule():
    policy = _policy(
        per_job={"db-backup": {"max_alerts": 7, "window_seconds": 300}},
    )
    rule = policy.rule_for("db-backup")
    assert rule.max_alerts == 7
    assert rule.window_seconds == 300
