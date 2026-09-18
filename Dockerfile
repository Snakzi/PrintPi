# syntax=docker/dockerfile:1.7
# PrintPi in one container: nginx, php-fpm, Redis and the printer daemon under supervisord, the
# same layout deploy/install.sh builds on a Pi. Persistent data lives in /var/lib/printpi, the
# printer and a camera come in with --device. See README.md, section "Docker".
ARG DEBIAN_RELEASE=trixie

# The frontend bundle and the Composer packages are architecture independent, so they are built
# once on the build host whatever platforms the image is built for.
FROM --platform=$BUILDPLATFORM node:24-bookworm-slim AS frontend
WORKDIR /src
COPY app/package.json app/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY app/ ./
RUN npm run build

FROM --platform=$BUILDPLATFORM composer:2 AS vendor
WORKDIR /src
COPY app/composer.json app/composer.lock ./
RUN composer install --no-dev --no-scripts --no-autoloader --prefer-dist --no-interaction --no-progress --ignore-platform-reqs
COPY app/ ./
RUN composer dump-autoload --no-dev --optimize --no-interaction --ignore-platform-reqs

# The daemon's virtualenv with the built-in plugins' requirements, compiled for the target platform.
FROM debian:${DEBIAN_RELEASE}-slim AS venv
ENV DEBIAN_FRONTEND=noninteractive PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv python3-dev gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*
COPY daemon /opt/printpi/daemon
COPY plugins /opt/printpi/plugins
RUN python3 -m venv /opt/printpi/venv \
    && /opt/printpi/venv/bin/pip install --upgrade pip \
    && /opt/printpi/venv/bin/pip install -e /opt/printpi/daemon \
    && for requirements in /opt/printpi/plugins/*/daemon/requirements.txt; do \
        /opt/printpi/venv/bin/pip install -r "$requirements"; \
    done

FROM debian:${DEBIAN_RELEASE}-slim
LABEL org.opencontainers.image.title="PrintPi" \
      org.opencontainers.image.description="Print server for Marlin printers: USB serial with a Laravel API and a Vue dashboard" \
      org.opencontainers.image.source="https://github.com/Snakzi/PrintPi" \
      org.opencontainers.image.licenses="MIT"
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        nginx redis-server supervisor \
        php-fpm php-cli php-sqlite3 php-xml php-mbstring php-curl php-zip \
        python3 ustreamer ffmpeg avrdude git ca-certificates curl tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 1000 --user-group --no-create-home --shell /usr/sbin/nologin printpi \
    && usermod -aG dialout,video printpi \
    && rm -f /etc/nginx/sites-enabled/default \
    && ln -sf /dev/stderr /var/log/nginx/error.log

COPY deploy/docker /opt/printpi/deploy/docker
# One socket path and a php-fpm binary whatever PHP version Debian ships; the pool keeps the
# container environment and forwards the workers' stderr so Laravel's log reaches docker logs.
RUN PHP_VERSION="$(php -r 'echo PHP_MAJOR_VERSION.".".PHP_MINOR_VERSION;')" \
    && ln -s "/usr/sbin/php-fpm$PHP_VERSION" /usr/local/sbin/php-fpm \
    && cp /opt/printpi/deploy/docker/php.ini "/etc/php/$PHP_VERSION/fpm/conf.d/99-printpi.ini" \
    && cp /opt/printpi/deploy/docker/php.ini "/etc/php/$PHP_VERSION/cli/conf.d/99-printpi.ini" \
    && sed -i -e 's|^listen = .*|listen = /run/php/php-fpm.sock|' \
        -e 's|^;\?clear_env = .*|clear_env = no|' \
        -e 's|^;\?catch_workers_output = .*|catch_workers_output = yes|' \
        -e 's|^;\?decorate_workers_output = .*|decorate_workers_output = no|' \
        "/etc/php/$PHP_VERSION/fpm/pool.d/www.conf" \
    && sed -i 's|^error_log = .*|error_log = /proc/self/fd/2|' "/etc/php/$PHP_VERSION/fpm/php-fpm.conf" \
    && install -d -o www-data -g www-data /run/php

COPY VERSION /opt/printpi/VERSION
COPY plugins /opt/printpi/plugins
COPY daemon /opt/printpi/daemon
COPY --from=venv --chown=printpi:printpi /opt/printpi/venv /opt/printpi/venv
COPY app /opt/printpi/app
COPY --from=vendor /src/vendor /opt/printpi/app/vendor
COPY --from=frontend /src/public/build /opt/printpi/app/public/build
RUN cd /opt/printpi/app \
    && php artisan package:discover --ansi --no-interaction \
    && chown -R www-data:www-data storage bootstrap/cache

ENV PRINTPI_HOME=/opt/printpi \
    PRINTPI_REDIS_URL=redis://127.0.0.1:6379/0 \
    PRINTPI_PORT=/dev/printer \
    PRINTPI_BAUD=115200 \
    PRINTPI_GCODE_DIR=/var/lib/printpi/gcode \
    PRINTPI_TIMELAPSE_DIR=/var/lib/printpi/timelapse \
    PRINTPI_PLUGINS_DIR=/var/lib/printpi/plugins \
    HTTP_PORT=80

VOLUME /var/lib/printpi
EXPOSE 80
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD curl -fsS "http://127.0.0.1:${HTTP_PORT}/api/v1/session" >/dev/null || exit 1
ENTRYPOINT ["/opt/printpi/deploy/docker/entrypoint.sh"]
