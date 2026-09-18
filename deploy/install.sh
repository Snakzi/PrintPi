#!/usr/bin/env bash
# PrintPi installer for Raspberry Pi OS Lite (64-bit, Bookworm or newer).
#
# Idempotent: run it after every deploy, it only changes what is missing.
#
#   sudo ./deploy/install.sh                        install this release and activate it
#   sudo PRINTPI_SER2NET=1 ./deploy/install.sh      also expose the printer on TCP 3333
#                                                   for development from another machine
#   PRINTPI_IMAGE_BUILD=1 ./deploy/install.sh       inside the chroot of scripts/build-image.sh: no
#                                                   services are started and everything that needs a
#                                                   running system (app key, database, plugin sync)
#                                                   waits for printpi-firstboot on the first boot
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
ENV_DIR=/etc/printpi
# Explicit overrides survive the persisted defaults used by unattended updates.
REQUESTED_HOME="${PRINTPI_HOME:-}"
REQUESTED_USER="${PRINTPI_USER:-}"
if [[ -f "$ENV_DIR/install.env" ]]; then
    # shellcheck disable=SC1091
    source "$ENV_DIR/install.env"
fi
PRINTPI_HOME="${REQUESTED_HOME:-${PRINTPI_HOME:-/opt/printpi}}"
RUN_USER="${REQUESTED_USER:-${PRINTPI_USER:-${SUDO_USER:-pi}}}"
PRINTPI_HOME="$(realpath -m "$PRINTPI_HOME")"
APP="$SRC/app"
IMAGE_BUILD="${PRINTPI_IMAGE_BUILD:-0}"
# Inside the image chroot `hostname` would name the build machine.
HOST="$(cat /etc/hostname 2>/dev/null || hostname)"

# `==> ` lines are the progress steps; the update helper mirrors them into the status
# file the web app shows, so they must stay free of colour codes when piped.
if [[ -t 1 ]]; then
    log() { printf '\033[1;32m==>\033[0m %s\n' "$*"; }
    note() { printf '\033[1;32m%s\033[0m\n' "$*"; }
else
    log() { printf '==> %s\n' "$*"; }
    note() { printf '%s\n' "$*"; }
fi
if [[ -t 2 ]]; then
    warn() { printf '\033[1;33m!!\033[0m %s\n' "$*" >&2; }
else
    warn() { printf '!! %s\n' "$*" >&2; }
fi

[[ $EUID -eq 0 ]] || { warn "run with sudo"; exit 1; }

if [[ "$SRC" != "$PRINTPI_HOME/releases/"* && "${PRINTPI_ALLOW_ANY_DIR:-0}" != 1 ]]; then
    warn "Release must be under $PRINTPI_HOME/releases/; use scripts/deploy.sh to deploy a checkout."
    exit 1
fi
[[ -d "$APP/vendor" ]] || { warn "$APP/vendor is missing; run composer install in app/ before deploying."; exit 1; }

log "Installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
# ffmpeg assembles the timelapse video, avrdude flashes 8-bit printer boards from the settings page.
apt-get install -y -qq nginx redis-server php-fpm php-cli php-sqlite3 php-xml php-mbstring php-curl php-zip \
    python3-venv python3-dev git rsync ustreamer minisign curl ffmpeg avrdude

# A persistent journal keeps the boot before a crash readable (journalctl -b -1). Pi OS
# forces a volatile journal through /usr/lib/systemd/journald.conf.d/40-rpi-volatile-storage.conf,
# so a directory alone does nothing; a drop-in in /etc overrides it, capped so the SD card stays small.
if [[ ! -f /etc/systemd/journald.conf.d/printpi.conf ]]; then
    mkdir -p /var/log/journal /etc/systemd/journald.conf.d
    printf '[Journal]\nStorage=persistent\nSystemMaxUse=100M\n' > /etc/systemd/journald.conf.d/printpi.conf
    systemd-tmpfiles --create --prefix /var/log/journal >/dev/null 2>&1 || true
    systemctl restart systemd-journald 2>/dev/null || true
fi

log "Setting up device access for $RUN_USER"
# kmem is for /dev/mem, which the LED strip plugin needs on PWM pins; gpio and spi only exist on Pi OS.
GROUPS_PRESENT=""
for group in dialout video gpio spi kmem; do
    if getent group "$group" >/dev/null; then
        usermod -aG "$group" "$RUN_USER"
        GROUPS_PRESENT="$GROUPS_PRESENT $group"
    fi
done
install -m 644 "$SRC/deploy/udev/99-printpi.rules" /etc/udev/rules.d/99-printpi.rules
# In the chroot /dev belongs to the build machine; the rules apply on the first boot instead.
if [[ "$IMAGE_BUILD" != 1 ]]; then
    udevadm control --reload-rules
    udevadm trigger --subsystem-match=tty || true
    if [[ -c /dev/mem ]] && getent group kmem >/dev/null; then
        chgrp kmem /dev/mem && chmod 0660 /dev/mem
    fi
    if [[ -c /dev/vcio ]]; then
        chgrp video /dev/vcio && chmod 0660 /dev/vcio
    fi
    if command -v raspi-config >/dev/null && [[ ! -e /dev/spidev0.0 ]]; then
        raspi-config nonint do_spi 0 && warn "SPI enabled for the LED strip plugin, active after a reboot"
    fi
fi

install -d -m 755 "$ENV_DIR" "$PRINTPI_HOME/releases" "$PRINTPI_HOME/downloads"
install -d -m 2775 -o "$RUN_USER" -g www-data /var/lib/printpi
if [[ -d "$PRINTPI_HOME/app" && ! -L "$PRINTPI_HOME/app" ]]; then
    [[ "$SRC" == "$PRINTPI_HOME/releases/"* ]] || { warn "Migrate from a release deployed with scripts/deploy.sh."; exit 1; }
    for pair in "app/database/database.sqlite:/var/lib/printpi/printpi.sqlite" \
        "app/storage/app/gcode:/var/lib/printpi/gcode" \
        "app/storage/app/timelapse:/var/lib/printpi/timelapse" "app/.env:$ENV_DIR/app.env"; do
        old="$PRINTPI_HOME/${pair%%:*}"
        target="${pair#*:}"
        if [[ -e "$old" && ! -e "$target" ]]; then
            log "Moving $old to $target"
            mv "$old" "$target"
        fi
    done
    find "$PRINTPI_HOME" -mindepth 1 -maxdepth 1 \
        ! -name releases ! -name current ! -name previous ! -name downloads -exec rm -rf -- {} +
fi
install -d -m 2775 -o "$RUN_USER" -g www-data \
    /var/lib/printpi/gcode /var/lib/printpi/timelapse /var/lib/printpi/backups
chown -R "$RUN_USER:$RUN_USER" "$SRC"

log "Installing the daemon"
if [[ ! -x "/var/lib/printpi/venv/bin/python" ]]; then
    sudo -u "$RUN_USER" python3 -m venv "/var/lib/printpi/venv"
fi
sudo -u "$RUN_USER" "/var/lib/printpi/venv/bin/pip" install -q --upgrade pip
sudo -u "$RUN_USER" "/var/lib/printpi/venv/bin/pip" install -q -e "$SRC/daemon"

log "Installing plugin requirements"
for requirements in "$SRC"/plugins/*/daemon/requirements.txt; do
    [[ -f "$requirements" ]] || continue
    if ! sudo -u "$RUN_USER" "/var/lib/printpi/venv/bin/pip" install -q -r "$requirements"; then
        warn "could not install $requirements; the daemon retries when the plugin is enabled"
    fi
done

mkdir -p "$ENV_DIR" /var/log/printpi
chown "$RUN_USER:$RUN_USER" /var/log/printpi
if [[ ! -f "$ENV_DIR/daemon.env" ]]; then
    install -m 640 -o root -g "$RUN_USER" "$SRC/deploy/daemon.env.example" "$ENV_DIR/daemon.env"
fi
if ! grep -q '^PRINTPI_TIMELAPSE_DIR=' "$ENV_DIR/daemon.env"; then
    printf '\nPRINTPI_TIMELAPSE_DIR=/var/lib/printpi/timelapse\n' >> "$ENV_DIR/daemon.env"
fi
chown "root:$RUN_USER" "$ENV_DIR/daemon.env"
chmod 640 "$ENV_DIR/daemon.env"
install -m 644 "$SRC/deploy/logrotate/printpi" /etc/logrotate.d/printpi
sed -e "s|__USER__|$RUN_USER|g" -e "s|__HOME__|$PRINTPI_HOME|g" -e "s|__GROUPS__|${GROUPS_PRESENT# }|g" \
    "$SRC/deploy/systemd/printpi-daemon.service" > /etc/systemd/system/printpi-daemon.service
install -m 755 "$SRC/deploy/bin/printpi-system" /usr/local/bin/printpi-system
install -m 440 "$SRC/deploy/sudoers/printpi" /etc/sudoers.d/printpi
visudo -cf /etc/sudoers.d/printpi >/dev/null
[[ "$IMAGE_BUILD" == 1 ]] || systemctl daemon-reload
if [[ "$IMAGE_BUILD" == 1 ]]; then
    systemctl enable redis-server >/dev/null
else
    systemctl enable --now redis-server >/dev/null
fi
systemctl enable printpi-daemon >/dev/null
log "Configuring the web app"
if [[ ! -f "$ENV_DIR/app.env" ]]; then
    cp "$APP/.env.example" "$ENV_DIR/app.env"
    sed -i -e 's|^APP_ENV=.*|APP_ENV=production|' -e 's|^APP_DEBUG=.*|APP_DEBUG=false|' \
        -e "s|^APP_URL=.*|APP_URL=http://$HOST.local|" "$ENV_DIR/app.env"
fi
for setting in APP_ENV=production APP_DEBUG=false "APP_URL=http://$HOST.local" APP_KEY= \
    PRINTPI_WEBCAM_BASE=/webcam DB_DATABASE=/var/lib/printpi/printpi.sqlite \
    PRINTPI_GCODE_DIR=/var/lib/printpi/gcode PRINTPI_TIMELAPSE_DIR=/var/lib/printpi/timelapse \
    PRINTPI_PLUGINS_DIR=/var/lib/printpi/plugins \
    "PRINTPI_UPDATE_URL=${PRINTPI_UPDATE_URL:-https://updates.194-164-58-152.sslip.io}" "PRINTPI_HOME=$PRINTPI_HOME"; do
    if ! grep -q "^${setting%%=*}=" "$ENV_DIR/app.env"; then
        printf '\n%s\n' "$setting" >> "$ENV_DIR/app.env"
    fi
done
chown "$RUN_USER:www-data" "$ENV_DIR/app.env"
chmod 640 "$ENV_DIR/app.env"
ln -sfn "$ENV_DIR/app.env" "$APP/.env"
UPDATE_URL="$(sed -n 's/^PRINTPI_UPDATE_URL=//p' "$ENV_DIR/app.env" | tail -n1)"
UPDATE_URL="${UPDATE_URL%\"}"; UPDATE_URL="${UPDATE_URL#\"}"
UPDATE_URL="${UPDATE_URL%\'}"; UPDATE_URL="${UPDATE_URL#\'}"
printf 'PRINTPI_USER=%q\nPRINTPI_HOME=%q\nPRINTPI_UPDATE_URL=%q\nPRINTPI_PANEL=%q\n' \
    "$RUN_USER" "$PRINTPI_HOME" "$UPDATE_URL" "${PRINTPI_PANEL:-0}" > "$ENV_DIR/install.env"
chown root:root "$ENV_DIR/install.env"
chmod 644 "$ENV_DIR/install.env"
if [[ -f "$SRC/deploy/update.pub" ]]; then
    install -m 644 "$SRC/deploy/update.pub" "$ENV_DIR/update.pub"
else
    warn "no update key in this release, updates from the UI are disabled until one is installed"
fi
[[ -f "$SRC/VERSION" ]] || warn "This release is missing VERSION"

cd "$APP"
# The app key is generated on the first boot of an image, so no two installs share one.
if [[ "$IMAGE_BUILD" != 1 ]] && ! grep -q '^APP_KEY=base64:' "$APP/.env"; then
    sudo -u "$RUN_USER" php "$APP/artisan" key:generate --force --quiet --no-interaction
fi
touch /var/lib/printpi/printpi.sqlite
chown "$RUN_USER:www-data" /var/lib/printpi/printpi.sqlite
# The data directories are shared between the daemon ($RUN_USER) and the web app (www-data) through
# the group, with setgid so new files inherit it. The sticky bit on the parent lets www-data add its
# SQLite journal files but not rename the venv or the data directories, which the daemon executes
# and reads with more privileges than the web app has.
chmod 3775 /var/lib/printpi
chgrp -R www-data /var/lib/printpi/printpi.sqlite /var/lib/printpi/gcode /var/lib/printpi/timelapse /var/lib/printpi/backups
chmod -R g+rwX /var/lib/printpi/printpi.sqlite /var/lib/printpi/gcode /var/lib/printpi/timelapse /var/lib/printpi/backups
find /var/lib/printpi/gcode /var/lib/printpi/timelapse /var/lib/printpi/backups -type d -exec chmod g+s {} +
chown -R "$RUN_USER:$RUN_USER" /var/lib/printpi/venv
# Plugins installed from git: the web app (www-data) clones here, the daemon reads.
install -d -m 2775 -o www-data -g "$RUN_USER" /var/lib/printpi/plugins
if [[ "$IMAGE_BUILD" == 1 ]]; then
    # The first boot migrates, caches and syncs once the key exists and Redis runs.
    install -m 755 "$SRC/deploy/bin/printpi-firstboot" /usr/local/bin/printpi-firstboot
    install -m 644 "$SRC/deploy/systemd/printpi-firstboot.service" /etc/systemd/system/printpi-firstboot.service
    systemctl enable printpi-firstboot >/dev/null
    touch "$ENV_DIR/firstboot"
else
    log "Migrating the database"
    sudo -u "$RUN_USER" php "$APP/artisan" migrate --force --quiet --no-interaction
    sudo -u "$RUN_USER" php "$APP/artisan" optimize --quiet --no-interaction
    # A release may change a built-in plugin manifest; Redis passes that list to the daemon.
    sudo -u "$RUN_USER" php "$APP/artisan" printpi:sync-plugins --quiet --no-interaction \
        || warn "Could not hand the plugins to the daemon; toggle a plugin in the UI to sync."
fi
chgrp -R www-data "$APP/storage" "$APP/bootstrap/cache"
chmod -R g+rwX "$APP/storage" "$APP/bootstrap/cache"

if [[ "$(readlink -f "$PRINTPI_HOME/current" || true)" != "$SRC" ]]; then
    log "Switching to $(cat "$SRC/VERSION" 2>/dev/null || basename "$SRC")"
    if [[ -e "$PRINTPI_HOME/current" ]]; then
        ln -sfn "$(readlink -f "$PRINTPI_HOME/current")" "$PRINTPI_HOME/previous"
    fi
    rm -f "$PRINTPI_HOME/current.tmp"
    ln -s "$SRC" "$PRINTPI_HOME/current.tmp" && mv -T "$PRINTPI_HOME/current.tmp" "$PRINTPI_HOME/current" \
        || { rm -f "$PRINTPI_HOME/current.tmp"; exit 1; }
fi

log "Restarting services"
PHP_FPM_UNITS=(/lib/systemd/system/php*-fpm.service)
PHP_FPM_UNIT="$(basename "${PHP_FPM_UNITS[0]}")"
PHP_VERSION="$(php -r 'echo PHP_MAJOR_VERSION.".".PHP_MINOR_VERSION;')"
cat > "/etc/php/$PHP_VERSION/fpm/conf.d/99-printpi.ini" <<'INI'
; G-code uploads are large; nginx allows 512M as well.
upload_max_filesize = 512M
post_max_size = 512M
max_execution_time = 300
INI
systemctl enable "$PHP_FPM_UNIT" >/dev/null
[[ "$IMAGE_BUILD" == 1 ]] || systemctl restart "$PHP_FPM_UNIT"
# In the chroot no socket exists yet; php-fpm creates it under this name on the first boot.
PHP_SOCK="/run/php/php$PHP_VERSION-fpm.sock"
if [[ "$IMAGE_BUILD" != 1 ]]; then
    PHP_SOCKS=(/run/php/php*-fpm.sock)
    PHP_SOCK="${PHP_SOCKS[0]}"
fi
sed -e "s|__HOME__|$PRINTPI_HOME|g" -e "s|__PHP_SOCK__|$PHP_SOCK|g" \
    "$SRC/deploy/nginx/printpi.conf" > /etc/nginx/sites-available/printpi
ln -sf /etc/nginx/sites-available/printpi /etc/nginx/sites-enabled/printpi
rm -f /etc/nginx/sites-enabled/default
nginx -t -q
if [[ "$IMAGE_BUILD" == 1 ]]; then
    systemctl enable nginx >/dev/null
else
    systemctl reload nginx
    # A restart ends a running print, so the new daemon code waits until the printer is free.
    if redis-cli get printpi:state 2>/dev/null | grep -Eq '"state": ?"(printing|paused|cancelling)"'; then
        warn "A print is running: the daemon keeps its old code until 'sudo systemctl restart printpi-daemon'"
    elif systemctl is-active --quiet printpi-daemon; then
        systemctl restart printpi-daemon
    else
        systemctl start printpi-daemon
    fi
fi

# The touch panel: a kiosk browser on the Pi's own screen. Switched on once with
# PRINTPI_PANEL=1 (remembered in install.env), it stays on for later installs.
if [[ "${PRINTPI_PANEL:-0}" == "1" ]]; then
    log "Installing the touch panel"
    apt-get install -y -qq cage chromium wlr-randr
    if [[ ! -f "$ENV_DIR/panel.env" ]]; then
        install -m 640 -o root -g "$RUN_USER" "$SRC/deploy/panel.env.example" "$ENV_DIR/panel.env"
    fi
    if ! grep -q '^PRINTPI_PANEL_TOKEN=.\+' "$ENV_DIR/panel.env"; then
        PANEL_TOKEN="$(head -c 64 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | cut -c1-40)"
        sed -i "s|^PRINTPI_PANEL_TOKEN=.*|PRINTPI_PANEL_TOKEN=$PANEL_TOKEN|" "$ENV_DIR/panel.env"
    fi
    PANEL_TOKEN="$(sed -n 's/^PRINTPI_PANEL_TOKEN=//p' "$ENV_DIR/panel.env")"
    if grep -q '^PRINTPI_PANEL_TOKEN=' "$ENV_DIR/app.env"; then
        sed -i "s|^PRINTPI_PANEL_TOKEN=.*|PRINTPI_PANEL_TOKEN=$PANEL_TOKEN|" "$ENV_DIR/app.env"
    else
        printf '\nPRINTPI_PANEL_TOKEN=%s\n' "$PANEL_TOKEN" >> "$ENV_DIR/app.env"
    fi
    install -m 755 "$SRC/deploy/bin/printpi-panel" /usr/local/bin/printpi-panel
    sed -e "s|__USER__|$RUN_USER|g" "$SRC/deploy/systemd/printpi-panel.service" > /etc/systemd/system/printpi-panel.service
    [[ "$IMAGE_BUILD" == 1 ]] || systemctl daemon-reload
    systemctl enable printpi-panel >/dev/null
    if [[ "$IMAGE_BUILD" != 1 ]]; then
        sudo -u "$RUN_USER" php "$APP/artisan" optimize --quiet --no-interaction
        systemctl restart printpi-panel
    fi
fi

if [[ "${PRINTPI_SER2NET:-0}" == "1" ]]; then
    log "ser2net for remote development"
    apt-get install -y -qq ser2net
    install -m 644 "$SRC/deploy/ser2net.yaml" /etc/ser2net.yaml
    systemctl enable ser2net >/dev/null
    [[ "$IMAGE_BUILD" == 1 ]] || systemctl restart ser2net
    warn "ser2net and the daemon cannot share the port. Before developing remotely: sudo systemctl stop printpi-daemon"
fi

if [[ "$IMAGE_BUILD" == 1 ]]; then
    note "Image prepared: the first boot finishes the setup, then http://$HOST.local runs the wizard."
    exit 0
fi
note "Done.  Daemon: journalctl -fu printpi-daemon   Serial: tail -f /var/log/printpi/serial.log   Web: http://$HOST.local"
if [[ "$(sudo -u "$RUN_USER" php "$APP/artisan" tinker --execute 'echo App\Models\User::query()->exists() ? "yes" : "no";' 2>/dev/null | tail -n1)" != "yes" ]]; then
    note "No account yet: open the web address above to run the setup wizard."
fi
