"""Tests for cronwatch.ratelimit."""

import pytest
from cronwatch.ratelimit import RateLimiter


BASE = 1_000.0  # arbitrary monotonic base


@pytest.fixture()
def limiter() -> RateLimiter:
    return RateLimiter(window_seconds=60.0, max_alerts=3)


def test_first_alert_always_allowed(limiter: RateLimiter) -> None:
    assert limiter.is_allowed("job_a", _now=BASE) is True


def test_record_then_check_counts(limiter: RateLimiter) -> None:
    limiter.record("job_a", _now=BASE)
    limiter.record("job_a", _now=BASE + 1)
    assert limiter.remaining("job_a", _now=BASE + 2) == 1


def test_exceeding_max_blocks(limiter: RateLimiter) -> None:
    for i in range(3):
        limiter.record("job_a", _now=BASE + i)
    assert limiter.is_allowed("job_a", _now=BASE + 3) is False


def test_old_entries_evicted_after_window(limiter: RateLimiter) -> None:
    for i in range(3):
        limiter.record("job_a", _now=BASE + i)
    # Advance past the 60-second window
    assert limiter.is_allowed("job_a", _now=BASE + 61) is True


def test_remaining_zero_when_exhausted(limiter: RateLimiter) -> None:
    for i in range(3):
        limiter.record("job_a", _now=BASE + i)
    assert limiter.remaining("job_a", _now=BASE + 3) == 0


def test_remaining_full_when_window_expired(limiter: RateLimiter) -> None:
    for i in range(3):
        limiter.record("job_a", _now=BASE + i)
    assert limiter.remaining("job_a", _now=BASE + 120) == 3


def test_reset_clears_state(limiter: RateLimiter) -> None:
    for i in range(3):
        limiter.record("job_a", _now=BASE + i)
    limiter.reset("job_a")
    assert limiter.is_allowed("job_a", _now=BASE + 3) is True


def test_different_jobs_are_independent(limiter: RateLimiter) -> None:
    for i in range(3):
        limiter.record("job_a", _now=BASE + i)
    assert limiter.is_allowed("job_b", _now=BASE + 3) is True


def test_invalid_window_raises() -> None:
    with pytest.raises(ValueError, match="window_seconds"):
        RateLimiter(window_seconds=0)


def test_invalid_max_raises() -> None:
    with pytest.raises(ValueError, match="max_alerts"):
        RateLimiter(max_alerts=0)


def test_partial_eviction_keeps_recent(limiter: RateLimiter) -> None:
    limiter.record("job_a", _now=BASE)        # will be evicted
    limiter.record("job_a", _now=BASE + 50)   # still in window
    limiter.record("job_a", _now=BASE + 55)   # still in window
    # At BASE+61 the first entry falls out; 2 remain → 1 slot left
    assert limiter.remaining("job_a", _now=BASE + 61) == 1
