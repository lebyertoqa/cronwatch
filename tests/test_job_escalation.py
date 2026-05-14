"""Tests for cronwatch.job_escalation."""
import pytest

from cronwatch.job_escalation import (
    EscalationLevel,
    EscalationPolicy,
    EscalationTracker,
)


def _policy() -> EscalationPolicy:
    return EscalationPolicy(
        levels=[
            EscalationLevel(name="warning", after_failures=1),
            EscalationLevel(name="critical", after_failures=3),
        ],
        default_level="info",
    )


def _tracker() -> EscalationTracker:
    return EscalationTracker(_policy())


def test_first_failure_returns_warning():
    t = _tracker()
    level = t.record_failure("backup")
    assert level == "warning"


def test_third_failure_returns_critical():
    t = _tracker()
    for _ in range(3):
        level = t.record_failure("backup")
    assert level == "critical"


def test_fourth_failure_stays_critical():
    t = _tracker()
    for _ in range(4):
        level = t.record_failure("backup")
    assert level == "critical"


def test_success_resets_consecutive_count():
    t = _tracker()
    t.record_failure("backup")
    t.record_failure("backup")
    t.record_success("backup")
    assert t.consecutive_failures("backup") == 0


def test_success_clears_current_level():
    t = _tracker()
    t.record_failure("backup")
    t.record_success("backup")
    assert t.current_level("backup") is None


def test_failure_after_success_starts_fresh():
    t = _tracker()
    t.record_failure("backup")
    t.record_failure("backup")
    t.record_success("backup")
    level = t.record_failure("backup")
    assert level == "warning"


def test_escalated_false_before_any_failure():
    t = _tracker()
    assert not t.escalated("backup")


def test_escalated_false_at_default_level():
    # policy default is "info"; first failure is "warning" which IS beyond default
    t = _tracker()
    t.record_failure("backup")
    assert t.escalated("backup")  # warning > info


def test_escalated_true_when_critical():
    t = _tracker()
    for _ in range(3):
        t.record_failure("backup")
    assert t.escalated("backup")


def test_independent_tracking_per_job():
    t = _tracker()
    t.record_failure("job_a")
    t.record_failure("job_a")
    t.record_failure("job_b")
    assert t.consecutive_failures("job_a") == 2
    assert t.consecutive_failures("job_b") == 1


def test_policy_no_levels_always_returns_default():
    policy = EscalationPolicy(levels=[], default_level="warning")
    tracker = EscalationTracker(policy)
    for _ in range(10):
        level = tracker.record_failure("job")
    assert level == "warning"


def test_level_for_zero_failures_returns_default():
    p = _policy()
    assert p.level_for(0) == "info"
