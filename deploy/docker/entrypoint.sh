#!/usr/bin/env bash
# Container entry point: prepares the data directory, the app environment and the mapped
# devices, then hands over to supervisord, which runs Redis, php-fpm, nginx and the daemon.
# Runs as root; every service drops to its own user with the permission scheme of
# deploy/install.sh: the daemon (printpi) and the web app (www-data) share the data
# directories through the group, setgid keeps new files in it.
set -euo pipefail

APP=/opt/printpi/app
DATA=/var/lib/printpi
HTTP_PORT="${HTTP_PORT:-80}"

log() { printf 'printpi: %s\n' "$*"; }
as_www() { setpriv --reuid=www-data --regid=www-data --init-groups "$@"; }
own_dir() {  # mode owner group dir...
    local mode="$1" owner="$2" group="$3"
    shift 3
    mkdir -p "$@"
    chown "$owner:$group" "$@"
    chmod "$mode" "$@"
}

own_dir 3775 printpi www-data "$DATA"
own_dir 2775 printpi www-data "$DATA/gcode" "$DATA/timelapse"
own_dir 2775 www-data printpi "$DATA/plugins"
own_dir 700 redis redis "$DATA/redis"
own_dir 755 www-data www-data /run/php
[[ -e "$DATA/printpi.sqlite" ]] || touch "$DATA/printpi.sqlite"
chown www-data:www-data "$DATA/printpi.sqlite"
chmod 660 "$DATA/printpi.sqlite"

# Devices passed with --device keep the host's owner and group inside the container.
for node in /dev/printer /dev/ttyACM* /dev/ttyUSB* /dev/video* /dev/spidev* /dev/gpiomem /dev/mem /dev/vcio; do
    [[ -c "$node" ]] || continue
    chgrp printpi "$node" && chmod g+rw "$node"
done

if [[ ! -f "$DATA/app.env" ]]; then
    log "creating $DATA/app.env"
    cat > "$DATA/app.env" <<'ENV'
APP_NAME=PrintPi
APP_ENV=production
APP_DEBUG=false
APP_KEY=
APP_URL=http://localhost
LOG_CHANNEL=stderr
LOG_LEVEL=info
DB_CONNECTION=sqlite
SESSION_DRIVER=database
CACHE_STORE=database
REDIS_CLIENT=predis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
PRINTPI_WEBCAM_BASE=/webcam
ENV
fi
# Paths the container fixes; a newer image may need a setting an older app.env lacks.
for setting in "DB_DATABASE=$DATA/printpi.sqlite" "PRINTPI_GCODE_DIR=$DATA/gcode" \
    "PRINTPI_TIMELAPSE_DIR=$DATA/timelapse" "PRINTPI_PLUGINS_DIR=$DATA/plugins" "PRINTPI_HOME=/opt/printpi"; do
    grep -q "^${setting%%=*}=" "$DATA/app.env" || printf '%s\n' "$setting" >> "$DATA/app.env"
done
chown www-data:www-data "$DATA/app.env"
chmod 600 "$DATA/app.env"
ln -sfn "$DATA/app.env" "$APP/.env"

mkdir -p "$APP/storage/logs" "$APP/storage/framework/cache/data" "$APP/storage/framework/sessions" \
    "$APP/storage/framework/views"
chown -R www-data:www-data "$APP/storage" "$APP/bootstrap/cache"
if ! grep -q '^APP_KEY=base64:' "$DATA/app.env"; then
    as_www php "$APP/artisan" key:generate --force --quiet --no-interaction
fi
as_www php "$APP/artisan" migrate --force --quiet --no-interaction
as_www php "$APP/artisan" optimize --quiet --no-interaction

sed "s|__PORT__|$HTTP_PORT|g" /opt/printpi/deploy/docker/nginx.conf > /etc/nginx/sites-enabled/printpi
nginx -t -q

log "PrintPi $(cat /opt/printpi/VERSION) listening on port $HTTP_PORT, data in $DATA"
exec /usr/bin/supervisord -c /opt/printpi/deploy/docker/supervisord.conf
