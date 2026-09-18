#!/usr/bin/env bash
# Hands the enabled plugins to the daemon once Redis answers, what deploy/install.sh does after
# every deploy: a new image may carry a changed built-in manifest. Runs once per container start.
set -euo pipefail

for _ in $(seq 1 60); do
    redis-cli -h 127.0.0.1 ping >/dev/null 2>&1 && break
    sleep 0.5
done
exec setpriv --reuid=www-data --regid=www-data --init-groups \
    php /opt/printpi/app/artisan printpi:sync-plugins --quiet --no-interaction
