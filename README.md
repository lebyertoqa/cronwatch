# cronwatch

Lightweight daemon that monitors cron job execution and sends alerts on failures.

## Installation

```bash
pip install cronwatch
```

## Usage

Add `cronwatch` as a wrapper around your cron commands:

```
# crontab -e
*/5 * * * * cronwatch --job "backup" -- /usr/local/bin/backup.sh
0 2 * * *   cronwatch --job "db-dump" --timeout 3600 -- /usr/local/bin/dump.sh
```

Start the daemon:

```bash
cronwatch daemon --config /etc/cronwatch/config.yaml
```

Example configuration (`config.yaml`):

```yaml
alerts:
  email: ops@example.com
  slack_webhook: https://hooks.slack.com/services/...

jobs:
  backup:
    max_duration: 300
    notify_on: [failure, timeout]
  db-dump:
    max_duration: 3600
    notify_on: [failure]
```

cronwatch will send an alert if a job exits with a non-zero status, exceeds its timeout, or stops running unexpectedly.

View job history:

```bash
cronwatch status
cronwatch logs --job backup --tail 50
```

## License

MIT