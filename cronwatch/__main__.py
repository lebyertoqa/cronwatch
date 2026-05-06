"""Entry point: python -m cronwatch <config.yaml>"""

import argparse
import logging
import sys

from cronwatch.alerting import EmailAlerter, NullAlerter
from cronwatch.config import load_config
from cronwatch.scheduler import Scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("cronwatch")


def _build_alerter(config):
    alert = config.alert
    if alert and alert.smtp_host and alert.recipients:
        return EmailAlerter(alert)
    logger.warning("No alert config — failures will only be logged")
    return NullAlerter()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cronwatch",
        description="Monitor cron job execution and alert on failures.",
    )
    parser.add_argument("config", help="Path to cronwatch YAML config file")
    parser.add_argument(
        "--poll", type=int, default=30, metavar="SECONDS",
        help="How often to poll for due jobs (default: 30)",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except FileNotFoundError as exc:
        logger.error("Config file not found: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to load config: %s", exc)
        return 1

    alerter = _build_alerter(config)
    scheduler = Scheduler(config, alerter)

    logger.info(
        "cronwatch started — monitoring %d job(s)", len(config.jobs)
    )
    scheduler.run_forever(poll_interval=args.poll)
    return 0  # unreachable in normal operation


if __name__ == "__main__":
    sys.exit(main())
