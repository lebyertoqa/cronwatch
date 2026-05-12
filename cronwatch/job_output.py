"""Utilities for capturing, truncating, and storing job output."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

DEFAULT_MAX_BYTES = 64 * 1024  # 64 KB


@dataclass
class CapturedOutput:
    stdout: str = ""
    stderr: str = ""
    truncated: bool = False

    @property
    def combined(self) -> str:
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(self.stderr)
        return "\n".join(parts)

    @property
    def is_empty(self) -> bool:
        return not self.stdout and not self.stderr


def truncate(text: str, max_bytes: int) -> tuple[str, bool]:
    """Return (possibly truncated text, was_truncated)."""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return text, False
    return encoded[:max_bytes].decode("utf-8", errors="replace"), True


def capture_output(
    stdout_raw: str,
    stderr_raw: str,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> CapturedOutput:
    """Truncate stdout and stderr independently and return a CapturedOutput."""
    stdout, trunc_out = truncate(stdout_raw, max_bytes)
    stderr, trunc_err = truncate(stderr_raw, max_bytes)
    return CapturedOutput(
        stdout=stdout,
        stderr=stderr,
        truncated=trunc_out or trunc_err,
    )


def format_for_alert(output: CapturedOutput, max_lines: int = 50) -> str:
    """Return a human-readable block suitable for inclusion in an alert."""
    sections: list[str] = []
    if output.stdout:
        lines = output.stdout.splitlines()[-max_lines:]
        sections.append("--- stdout ---\n" + "\n".join(lines))
    if output.stderr:
        lines = output.stderr.splitlines()[-max_lines:]
        sections.append("--- stderr ---\n" + "\n".join(lines))
    if output.truncated:
        sections.append("[output truncated]")
    return "\n".join(sections) if sections else "(no output)"
