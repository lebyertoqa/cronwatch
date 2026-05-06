"""Alert dispatching for cronwatch — sends notifications on job failures."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from cronwatch.alerting_types import AlertConfig
from cronwatch.executor import ExecutionResult

logger = logging.getLogger(__name__)


class Alerter(Protocol):
    """Protocol that all alert backends must satisfy."""

    def send(self, result: ExecutionResult) -> None:
        ...


class EmailAlerter:
    """Sends failure alerts via SMTP email."""

    def __init__(self, config: AlertConfig) -> None:
        self.config = config

    def send(self, result: ExecutionResult) -> None:
        if not self.config.email:
            logger.debug("No email recipients configured; skipping email alert.")
            return

        msg = EmailMessage()
        msg["Subject"] = f"[cronwatch] Job '{result.job_name}' FAILED"
        msg["From"] = self.config.smtp_from
        msg["To"] = ", ".join(self.config.email)
        msg.set_content(
            f"Job: {result.job_name}\n"
            f"Exit code: {result.exit_code}\n"
            f"Duration: {result.duration:.2f}s\n\n"
            f"--- stdout ---\n{result.stdout or '(empty)'}\n\n"
            f"--- stderr ---\n{result.stderr or '(empty)'}\n"
        )

        try:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as smtp:
                if self.config.smtp_tls:
                    smtp.starttls()
                if self.config.smtp_user and self.config.smtp_password:
                    smtp.login(self.config.smtp_user, self.config.smtp_password)
                smtp.send_message(msg)
            logger.info("Alert email sent for job '%s'.", result.job_name)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to send alert email for job '%s': %s", result.job_name, exc)


def dispatch_alert(result: ExecutionResult, config: AlertConfig) -> None:
    """Dispatch an alert for a failed job using all configured backends."""
    if result.success:
        return
    alerter = EmailAlerter(config)
    alerter.send(result)
