"""Tests for cronwatch.job_output."""
import pytest

from cronwatch.job_output import (
    CapturedOutput,
    capture_output,
    format_for_alert,
    truncate,
    DEFAULT_MAX_BYTES,
)


# ---------------------------------------------------------------------------
# truncate
# ---------------------------------------------------------------------------

def test_truncate_short_string_unchanged():
    text = "hello world"
    result, was_truncated = truncate(text, 100)
    assert result == text
    assert was_truncated is False


def test_truncate_long_string_is_shortened():
    text = "a" * 200
    result, was_truncated = truncate(text, 100)
    assert len(result.encode("utf-8")) <= 100
    assert was_truncated is True


def test_truncate_exact_boundary_not_truncated():
    text = "b" * 50
    result, was_truncated = truncate(text, 50)
    assert result == text
    assert was_truncated is False


# ---------------------------------------------------------------------------
# capture_output
# ---------------------------------------------------------------------------

def test_capture_output_short_inputs():
    out = capture_output("hello", "world")
    assert out.stdout == "hello"
    assert out.stderr == "world"
    assert out.truncated is False


def test_capture_output_truncates_large_stdout():
    big = "x" * (DEFAULT_MAX_BYTES + 100)
    out = capture_output(big, "")
    assert out.truncated is True
    assert len(out.stdout.encode("utf-8")) <= DEFAULT_MAX_BYTES


def test_capture_output_truncates_large_stderr():
    big = "y" * (DEFAULT_MAX_BYTES + 100)
    out = capture_output("", big)
    assert out.truncated is True


def test_capture_output_empty_inputs():
    out = capture_output("", "")
    assert out.is_empty is True
    assert out.truncated is False


# ---------------------------------------------------------------------------
# CapturedOutput helpers
# ---------------------------------------------------------------------------

def test_combined_joins_stdout_and_stderr():
    out = CapturedOutput(stdout="line1", stderr="line2")
    assert "line1" in out.combined
    assert "line2" in out.combined


def test_combined_empty_when_both_empty():
    out = CapturedOutput()
    assert out.combined == ""


def test_is_empty_true_when_no_content():
    assert CapturedOutput().is_empty is True


def test_is_empty_false_when_stdout_present():
    assert CapturedOutput(stdout="data").is_empty is False


# ---------------------------------------------------------------------------
# format_for_alert
# ---------------------------------------------------------------------------

def test_format_for_alert_no_output_returns_placeholder():
    out = CapturedOutput()
    assert format_for_alert(out) == "(no output)"


def test_format_for_alert_includes_stdout_section():
    out = CapturedOutput(stdout="ok")
    result = format_for_alert(out)
    assert "--- stdout ---" in result
    assert "ok" in result


def test_format_for_alert_includes_stderr_section():
    out = CapturedOutput(stderr="err")
    result = format_for_alert(out)
    assert "--- stderr ---" in result


def test_format_for_alert_shows_truncated_notice():
    out = CapturedOutput(stdout="data", truncated=True)
    assert "[output truncated]" in format_for_alert(out)


def test_format_for_alert_respects_max_lines():
    many_lines = "\n".join(str(i) for i in range(200))
    out = CapturedOutput(stdout=many_lines)
    result = format_for_alert(out, max_lines=10)
    content_lines = [l for l in result.splitlines() if not l.startswith("---")]
    assert len(content_lines) <= 10
