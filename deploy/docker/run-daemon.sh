#!/usr/bin/env bash
# Runs the daemon as the printpi user. CAP_SYS_RAWIO is kept when the container was given it
# (--cap-add SYS_RAWIO or --privileged), the LED strip plugin needs it for /dev/mem on PWM pins;
# otherwise the capability is simply not there and the daemon runs without it.
set -euo pipefail

cd /opt/printpi/daemon
caps=()
if setpriv --inh-caps +sys_rawio --ambient-caps +sys_rawio true 2>/dev/null; then
    caps=(--inh-caps +sys_rawio --ambient-caps +sys_rawio)
fi
exec setpriv --reuid=printpi --regid=printpi --init-groups "${caps[@]}" \
    /opt/printpi/venv/bin/python -m printpi_daemon
