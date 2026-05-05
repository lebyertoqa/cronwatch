"""Tests for cronwatch.config module."""

import os
import textwrap
import pytest

from cronwatch.config import load_config, CronwatchConfig, JobConfig, AlertConfig


MINIMAL_YAML = textwrap.dedent("""\
    jobs:
      - name: test-job
        schedule: "* * * * *"
        command: /bin/true
""")

FULL_YAML = textwrap.dedent("""\
    log_file: /tmp/cw.log
    state_dir: /tmp/cw_state
    check_interval: 30
    alert:
      email: admin@example.com
      smtp_host: mail.example.com
      smtp_port: 465
      smtp_from: cw@example.com
      webhook_url: https://example.com/hook
    jobs:
      - name: backup
        schedule: "0 1 * * *"
        command: /bin/backup.sh
        timeout: 900
        alert_on_failure: true
        alert_on_timeout: false
        notify:
          - dev@example.com
""")


@pytest.fixture
def config_file(tmp_path):
    def _write(content):
        p = tmp_path / "cronwatch.yaml"
        p.write_text(content)
        return str(p)
    return _write


def test_load_minimal_config(config_file):
    cfg = load_config(config_file(MINIMAL_YAML))
    assert isinstance(cfg, CronwatchConfig)
    assert len(cfg.jobs) == 1
    job = cfg.jobs[0]
    assert job.name == "test-job"
    assert job.schedule == "* * * * *"
    assert job.command == "/bin/true"
    assert job.timeout == 3600
    assert job.alert_on_failure is True


def test_load_full_config(config_file):
    cfg = load_config(config_file(FULL_YAML))
    assert cfg.log_file == "/tmp/cw.log"
    assert cfg.state_dir == "/tmp/cw_state"
    assert cfg.check_interval == 30
    assert cfg.alert.email == "admin@example.com"
    assert cfg.alert.smtp_port == 465
    assert cfg.alert.webhook_url == "https://example.com/hook"
    job = cfg.jobs[0]
    assert job.name == "backup"
    assert job.timeout == 900
    assert job.alert_on_timeout is False
    assert "dev@example.com" in job.notify


def test_file_not_found():
    with pytest.raises(FileNotFoundError, match="Config file not found"):
        load_config("/nonexistent/path/cronwatch.yaml")


def test_empty_config(config_file):
    cfg = load_config(config_file(""))
    assert cfg.jobs == []
    assert isinstance(cfg.alert, AlertConfig)
