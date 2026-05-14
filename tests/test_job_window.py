"""Tests for cronwatch.job_window."""
from __future__ import annotations

import datetime

import pytest

from cronwatch.job_window import (
    WindowPolicy,
    WindowSkipResult,
    parse_window,
    within_window,
)


def _t(hour: int, minute: int = 0) -> datetime.time:
    return datetime.time(hour, minute)


def _dt(hour: int, minute: int = 0) -> datetime.datetime:
    return datetime.datetime(2024, 6, 15, hour, minute, 0)


# ---------------------------------------------------------------------------
# parse_window
# ---------------------------------------------------------------------------

def test_parse_window_valid():
    start, end = parse_window("08:00-18:00")
    assert start == _t(8)
    assert end == _t(18)


def test_parse_window_with_spaces():
    start, end = parse_window(" 09:30 - 17:45 ")
    assert start == _t(9, 30)
    assert end == _t(17, 45)


def test_parse_window_invalid_raises():
    with pytest.raises(ValueError):
        parse_window("not-a-window")


def test_parse_window_missing_separator_raises():
    with pytest.raises(ValueError):
        parse_window("0800")


# ---------------------------------------------------------------------------
# within_window
# ---------------------------------------------------------------------------

def test_empty_windows_always_true():
    assert within_window([], at=_dt(3)) is True


def test_inside_single_window():
    windows = [(_t(8), _t(18))]
    assert within_window(windows, at=_dt(12)) is True


def test_before_window_returns_false():
    windows = [(_t(8), _t(18))]
    assert within_window(windows, at=_dt(7, 59)) is False


def test_after_window_returns_false():
    windows = [(_t(8), _t(18))]
    assert within_window(windows, at=_dt(18, 1)) is False


def test_on_window_boundary_start():
    windows = [(_t(8), _t(18))]
    assert within_window(windows, at=_dt(8, 0)) is True


def test_on_window_boundary_end():
    windows = [(_t(8), _t(18))]
    assert within_window(windows, at=_dt(18, 0)) is True


def test_wrapping_window_inside_after_midnight():
    # 22:00-06:00 wraps midnight
    windows = [(_t(22), _t(6))]
    assert within_window(windows, at=_dt(2)) is True


def test_wrapping_window_inside_before_midnight():
    windows = [(_t(22), _t(6))]
    assert within_window(windows, at=_dt(23)) is True


def test_wrapping_window_outside():
    windows = [(_t(22), _t(6))]
    assert within_window(windows, at=_dt(12)) is False


def test_multiple_windows_matches_second():
    windows = [(_t(8), _t(10)), (_t(14), _t(16))]
    assert within_window(windows, at=_dt(15)) is True


def test_multiple_windows_no_match():
    windows = [(_t(8), _t(10)), (_t(14), _t(16))]
    assert within_window(windows, at=_dt(12)) is False


# ---------------------------------------------------------------------------
# WindowPolicy
# ---------------------------------------------------------------------------

def test_policy_returns_empty_for_unknown_job():
    policy = WindowPolicy(windows={})
    assert policy.windows_for("backup") == []


def test_policy_returns_configured_windows():
    w = [(_t(9), _t(17))]
    policy = WindowPolicy(windows={"deploy": w})
    assert policy.windows_for("deploy") == w


def test_policy_returns_copy_not_reference():
    w = [(_t(9), _t(17))]
    policy = WindowPolicy(windows={"deploy": w})
    result = policy.windows_for("deploy")
    result.append((_t(0), _t(1)))
    assert len(policy.windows_for("deploy")) == 1


# ---------------------------------------------------------------------------
# WindowSkipResult
# ---------------------------------------------------------------------------

def test_skip_result_skipped_is_true():
    result = WindowSkipResult(
        job_name="nightly",
        windows=[(_t(8), _t(18))],
        checked_at=_dt(3),
    )
    assert result.skipped is True


def test_skip_result_str_contains_job_name():
    result = WindowSkipResult(
        job_name="nightly",
        windows=[(_t(8), _t(18))],
        checked_at=_dt(3),
    )
    assert "nightly" in str(result)
