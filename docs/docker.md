# PrintPi in Docker

One container with nginx, php-fpm, Redis, the daemon and ustreamer under supervisord. Built for
amd64 and arm64 on every push to `main` (`latest`) and every release (the version number), at
`ghcr.io/snakzi/printpi`.

```bash
docker run -d --name printpi --restart unless-stopped \
  -p 8050:80 \
  -v printpi-data:/var/lib/printpi \
  --device /dev/ttyACM0:/dev/printer \
  ghcr.io/snakzi/printpi:latest
```

PrintPi is then at http://localhost:8050; change the left side of `-p` for another port. Or take
`compose.yaml` from the repository, fix the devices and `docker compose up -d`.

- `/var/lib/printpi` is the data: SQLite database, uploads, timelapses, plugins from git, the Redis
  snapshot and `app.env` with the app key. Don't lose it.
- The printer has to show up as `/dev/printer` inside the container, that is the name the daemon
  looks for. A camera comes in with `--device /dev/video0`.
- `HTTP_PORT` moves nginx off port 80 inside the container (you want that with `--network host`), `TZ` sets the timezone,
  `PRINTPI_SERIAL_LOG=/var/lib/printpi/serial.log` logs every line on the wire. That file grows
  forever, there is no logrotate in the container.
- The Tapo plugin finds plugs by UDP broadcast, which does not cross Docker's bridge. `--network host`
  fixes that. Plugs you added once are reached by address anyway.
- The LED strip plugin on PWM pins needs `--privileged` because it writes `/dev/mem`. On SPI pins
  `--device /dev/spidev0.0` is enough.
- Updating is `docker compose pull && docker compose up -d`. The update card, reboot and restart in
  the settings are disabled inside the container.

## Mac and Windows

Docker Desktop cannot pass USB through, so the printer needs a serial bridge: ser2net on the Pi
(`PRINTPI_SER2NET=1` for the installer) and `-e PRINTPI_PORT=rfc2217://printpi.local:3333`, or the
printer on the Mac itself behind
`socat TCP-LISTEN:3333,reuseaddr,fork FILE:/dev/tty.usbmodemXXXX,raw,echo=0,b115200` and
`-e PRINTPI_PORT=socket://host.docker.internal:3333`. The camera is then any MJPEG URL.
`-e PRINTPI_PORT=fake://` gives you a simulated printer if you just want to click around.

## Building it yourself

`docker build -t printpi .` in the repository, then
`docker run -d -p 8080:80 -e PRINTPI_PORT=fake:// printpi`.
