"""Tests for cronwatch.alerting."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cronwatch.alerting import EmailAlerter, dispatch_alert
from cronwatch.config import AlertConfig
from cronwatch.executor import ExecutionResult


def make_alert_config(**kwargs) -> AlertConfig:
    defaults = dict(
        email=["ops@example.com"],
        smtp_host="localhost",
        smtp_port=25,
        smtp_from="cronwatch@example.com",
        smtp_tls=False,
        smtp_user=None,
        smtp_password=None,
    )
    defaults.update(kwargs)
    return AlertConfig(**defaults)


def make_result(success: bool = False, exit_code: int = 1) -> ExecutionResult:
    return ExecutionResult(
        job_name="backup",
        success=success,
        exit_code=exit_code,
        stdout="some output",
        stderr="some error",
        duration=3.14,
    )


class TestEmailAlerter:
    def test_send_calls_smtp(self):
        config = make_alert_config()
        alerter = EmailAlerter(config)
        result = make_result(success=False)

        with patch("cronwatch.alerting.smtplib.SMTP") as mock_smtp_cls:
            mock_smtp = MagicMock()
            mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
            alerter.send(result)
            mock_smtp.send_message.assert_called_once()

    def test_send_skips_when_no_recipients(self):
        config = make_alert_config(email=[])
        alerter = EmailAlerter(config)
        result = make_result(success=False)

        with patch("cronwatch.alerting.smtplib.SMTP") as mock_smtp_cls:
            alerter.send(result)
            mock_smtp_cls.assert_not_called()

    def test_send_uses_starttls_when_configured(self):
        config = make_alert_config(smtp_tls=True)
        alerter = EmailAlerter(config)
        result = make_result(success=False)

        with patch("cronwatch.alerting.smtplib.SMTP") as mock_smtp_cls:
            mock_smtp = MagicMock()
            mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
            alerter.send(result)
            mock_smtp.starttls.assert_called_once()

    def test_send_logs_on_smtp_error(self, caplog):
        import logging
        config = make_alert_config()
        alerter = EmailAlerter(config)
        result = make_result(success=False)

        with patch("cronwatch.alerting.smtplib.SMTP", side_effect=OSError("conn refused")):
            with caplog.at_level(logging.ERROR, logger="cronwatch.alerting"):
                alerter.send(result)  # should not raise
        assert "conn refused" in caplog.text


class TestDispatchAlert:
    def test_no_alert_on_success(self):
        config = make_alert_config()
        result = make_result(success=True, exit_code=0)

        with patch("cronwatch.alerting.EmailAlerter.send") as mock_send:
            dispatch_alert(result, config)
            mock_send.assert_not_called()

    def test_alert_dispatched_on_failure(self):
        config = make_alert_config()
        result = make_result(success=False)

        with patch("cronwatch.alerting.EmailAlerter.send") as mock_send:
            dispatch_alert(result, config)
            mock_send.assert_called_once_with(result)
