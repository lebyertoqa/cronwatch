"""Tests for cronwatch.job_backoff."""
import math
import pytest

from cronwatch.job_backoff import (
    BackoffPolicy,
    BackoffStrategy,
    build_backoff_policy,
    delay_seconds,
    delays_for,
)


# ---------------------------------------------------------------------------
# delay_seconds
# ---------------------------------------------------------------------------

def test_first_attempt_equals_base():
    s = BackoffStrategy(base_seconds=10.0, multiplier=2.0, max_seconds=300.0)
    assert delay_seconds(s, 1) == pytest.approx(10.0)


def test_second_attempt_doubles():
    s = BackoffStrategy(base_seconds=10.0, multiplier=2.0, max_seconds=300.0)
    assert delay_seconds(s, 2) == pytest.approx(20.0)


def test_third_attempt_quadruples():
    s = BackoffStrategy(base_seconds=10.0, multiplier=2.0, max_seconds=300.0)
    assert delay_seconds(s, 3) == pytest.approx(40.0)


def test_delay_capped_at_max():
    s = BackoffStrategy(base_seconds=10.0, multiplier=4.0, max_seconds=50.0)
    # 10 * 4^3 = 640 > 50
    assert delay_seconds(s, 4) == pytest.approx(50.0)


def test_delay_at_exact_max_boundary():
    s = BackoffStrategy(base_seconds=10.0, multiplier=2.0, max_seconds=20.0)
    # 10 * 2^1 = 20 == max
    assert delay_seconds(s, 2) == pytest.approx(20.0)


def test_invalid_attempt_raises():
    s = BackoffStrategy()
    with pytest.raises(ValueError):
        delay_seconds(s, 0)


def test_negative_attempt_raises():
    s = BackoffStrategy()
    with pytest.raises(ValueError):
        delay_seconds(s, -1)


# ---------------------------------------------------------------------------
# delays_for
# ---------------------------------------------------------------------------

def test_delays_for_length():
    s = BackoffStrategy(base_seconds=5.0, multiplier=2.0, max_seconds=999.0)
    result = delays_for(s, 4)
    assert len(result) == 4


def test_delays_for_values_ascending():
    s = BackoffStrategy(base_seconds=5.0, multiplier=2.0, max_seconds=999.0)
    result = delays_for(s, 4)
    assert result == [pytest.approx(v) for v in [5.0, 10.0, 20.0, 40.0]]


def test_delays_for_zero_attempts_returns_empty():
    s = BackoffStrategy()
    assert delays_for(s, 0) == []


# ---------------------------------------------------------------------------
# BackoffPolicy
# ---------------------------------------------------------------------------

def test_policy_returns_default_for_unknown_job():
    policy = BackoffPolicy()
    assert policy.strategy_for("unknown") is policy.default


def test_policy_returns_per_job_strategy():
    custom = BackoffStrategy(base_seconds=1.0)
    policy = BackoffPolicy(per_job={"myjob": custom})
    assert policy.strategy_for("myjob") is custom


# ---------------------------------------------------------------------------
# build_backoff_policy
# ---------------------------------------------------------------------------

def test_build_uses_defaults():
    policy = build_backoff_policy()
    assert policy.default.base_seconds == pytest.approx(5.0)
    assert policy.default.multiplier == pytest.approx(2.0)
    assert policy.default.max_seconds == pytest.approx(300.0)


def test_build_per_job_override():
    policy = build_backoff_policy(
        per_job={"slow_job": {"base_seconds": 30.0, "multiplier": 3.0}}
    )
    s = policy.strategy_for("slow_job")
    assert s.base_seconds == pytest.approx(30.0)
    assert s.multiplier == pytest.approx(3.0)
    # max_seconds falls back to default
    assert s.max_seconds == pytest.approx(300.0)


def test_build_per_job_does_not_affect_default():
    policy = build_backoff_policy(per_job={"x": {"base_seconds": 1.0}})
    assert policy.default.base_seconds == pytest.approx(5.0)
