# Developing PrintPi

## Layout

```
daemon/    Python daemon: owns the serial port, Marlin protocol, print jobs, fake printer, tests
app/       Laravel 13 + Vue 3: API under /api/v1, pages for dashboard, files, terminal, camera, plugins, settings
plugins/   Built-in plugins (LED strip, bed level visualizer, Tapo plug); each has a manifest and a daemon part
deploy/    install.sh for the Pi, systemd unit, nginx, udev rule, ser2net, logrotate, docker/ for the container
scripts/   deploy.sh: build the frontend, rsync to the Pi, run install.sh there; release.sh and publish.sh for updates
Dockerfile, compose.yaml   one container with nginx, php-fpm, Redis and the daemon, published to GHCR
```

Daemon and web app only talk through Redis, see `daemon/printpi_daemon/bridge.py`:

| Key / channel        | Direction    | Content                                                        |
| -------------------- | ------------ | -------------------------------------------------------------- |
| `printpi:state`      | daemon → app | key with the current state as JSON (including the print job), plus a channel |
| `printpi:ports`      | daemon → app | key with the visible serial ports                              |
| `printpi:serial`     | daemon → app | channel with every line on the wire                            |
| `printpi:serial:log` | daemon → app | list of the last 500 lines for the terminal                    |
| `printpi:events`     | daemon → app | results and errors of commands                                 |
| `printpi:heartbeat`  | daemon → app | key refreshed every 3 s so the app knows the daemon is alive   |
| `printpi:plugins`    | app → daemon | key with the enabled plugins and their settings                |
| `printpi:commands`   | app → daemon | channel: `{"type":"connect","port":"/dev/ttyACM0","baud":115200}`, `{"type":"gcode","command":"G28"}`, `{"type":"print_start","path":"…"}`, `print_pause`, `print_resume`, `print_cancel`, `print_restart` |

## Development on the Mac

### Daemon

```bash
cd daemon
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```

Interactively against the fake printer, type G-code, `/help` lists the commands (`/print FILE`
streams a file, `/pause`, `/resume`, `/cancel` and `/again` control it):

```bash
daemon/.venv/bin/printpi-daemon --repl
```

Against the real printer on the Mac or through ser2net on the Pi:

```bash
daemon/.venv/bin/printpi-daemon --repl --port /dev/tty.usbmodem1234 --serial-log serial.log
daemon/.venv/bin/printpi-daemon --repl --port rfc2217://printer.local:3333 --serial-log serial.log
```

The fake takes options in the URL: `fake://?time_scale=0.1&latency=0.05&resend_every=20`.
The serial log is the most important debugging tool, every line with timestamp and direction.

### Web app

Redis must be running, then the daemon with the bridge, Laravel and Vite:

```bash
redis-server
daemon/.venv/bin/printpi-daemon --redis redis://127.0.0.1:6379/0
cd app && composer install && npm install && php artisan serve
cd app && npm run dev
```

On the first visit to http://localhost:8000 a wizard walks through account, hostname, printer,
port and camera; afterwards the app is behind a login. The daemon does not connect on its own:
pick the port on the dashboard, "Simulated printer" for development, and click connect. Tests
with `php artisan test --compact`, formatting with `vendor/bin/pint`.

### Talking to the printer from the Mac while it hangs on the Pi

```bash
ssh pi@printer.local 'sudo PRINTPI_SER2NET=1 /opt/printpi/deploy/install.sh && sudo systemctl stop printpi-daemon'
daemon/.venv/bin/printpi-daemon --repl --port rfc2217://printer.local:3333
```

The daemon and ser2net cannot share the port, so stop the daemon first and start it again with
`sudo systemctl start printpi-daemon` afterwards.

## Continuous integration

Two GitHub Actions workflows run on every push to `main`: `tests.yml` (the daemon's pytest, the
web app's PHPUnit and Pint check, the JavaScript tests and a production build of the frontend,
on GitHub's runners) and `docker.yml` (the container image for amd64 and arm64 on the self-hosted
runner, pushed to `ghcr.io/snakzi/printpi`). The README shows both as badges.

## Status

Done: setup wizard with admin account, hostname, printer profiles, port and camera, login,
connection with port selection, handshake, temperatures with presets and history chart, jog,
extruder, fans, terminal, G-code upload with slicer metadata, thumbnails and 3D preview, settings,
USB camera stream through ustreamer, plugin system with the LED strip, bed level visualizer and Tapo
plug plugins, printing with pause,
cancel and print again, a print job widget with elapsed and remaining time, a live 3D preview
of the running print, and printer firmware updates (Buddy boards from their USB drive with
M997, 8-bit boards with avrdude, other Marlin boards by restart). Tested against the fake printer
and the real Prusa MK4S over the serial port; the print job and the firmware update have only
run against the fake so far.

Next: Reverb instead of polling, the camera stream on the Pi, later a ready-made image with
CustomPiOS.
