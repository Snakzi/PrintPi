# Writing a plugin

A plugin is a directory with a `plugin.json` manifest and a Python file the daemon loads. The
web app owns the manifest, the install state and the settings; the daemon runs the code. Plugins
ship no frontend: the settings form and the dashboard controls are generated from the manifest.

```
my-plugin/
├── plugin.json              manifest: id, name, version, settings, controls
└── daemon/
    ├── plugin.py            class Plugin(PluginBase)
    └── requirements.txt     optional, pip-installed into the daemon's venv once
```

Built-in plugins live in `plugins/` of the repository. Anyone else's plugin is installed from a
git URL on the Plugins page (or `POST /api/v1/plugins {url}`) and cloned to
`/var/lib/printpi/plugins/<id>` on the Pi (`app/storage/app/plugins` on a dev machine). The
built-in ones are the best examples: `led-strip` (hardware, a light for the status bar),
`bed-level-visualizer` (G-code and a panel control), `tapo-plug` (network devices, a worker
thread, the printer's power switch, an auto-off after the print) and `webhook` (events posted
to a URL, notifications in the UI).

## plugin.json

```json
{
  "id": "nozzle-cam-light",
  "name": "Nozzle cam light",
  "version": "1.0.0",
  "description": "Switches the light over the nozzle camera.",
  "author": "you",
  "homepage": "https://github.com/you/printpi-nozzle-cam-light",
  "icon": "bulb",
  "daemon": true,
  "settings": [
    { "key": "gpio_pin", "label": "GPIO pin", "type": "integer", "default": 17, "min": 2, "max": 27 },
    { "key": "invert", "label": "Active low", "type": "boolean", "default": false }
  ],
  "controls": [
    { "key": "on", "label": "Light", "type": "toggle", "action": "set_on" }
  ]
}
```

| Field | |
|---|---|
| `id` | `a-z`, digits, `-` and `_`, up to 64 characters. Also the directory name after a git install. |
| `name`, `version` | Shown on the plugin page. A new version makes the daemon reload the module. |
| `description`, `author`, `homepage`, `icon` | Optional. `icon` is one of the app's icon names: `bulb`, `bolt`, `puzzle`, `camera`, `chip`, `fire`, `power`, `gauge`, `grid`, `printer`, `nozzle`, `bed`, `spool`, `server`, `link`, `clock`, `chart`, `photo` and a few more from `Icon.vue`. |
| `daemon` | `true` when there is a `daemon/plugin.py`. |
| `settings` | The form on the plugin page. Values arrive validated in `self.settings`. |
| `controls` | The rows on the plugin page and the dashboard widget. |

### Settings

Each entry has `key` (`a-z`, digits, `_`), `label`, `type` and optionally `default`. The types are
`string`, `password`, `text` (multi-line), `integer`, `number` (both with optional `min` and `max`),
`boolean`, `select` (with `options: [{value, label}]`) and `color` (`#rrggbb`). Without a default a
number is its `min` or 0, a select its first option, a string empty.

### Controls

Each entry has `key`, `label`, `type` and the `action` the daemon receives. Row controls:

| Type | Sends | Reads its value from `status()[key]` |
|---|---|---|
| `toggle` | `true` / `false` | boolean |
| `color` | `#rrggbb` | string |
| `range` | a number; takes `min`, `max`, `step`, `unit` | number |
| `select` | an option value; takes `options` | value |
| `text` | the string | string |
| `button` | `null` | – |

A control may list further action names under `actions`; the app only forwards actions that a
control names and refuses everything else. A value may be a scalar or a flat object of
scalars.

`mesh` and `devices` are panel controls with their own components. `mesh` expects
`status()[key]` to be `{probing, error, tolerance, measured_at, rows, cols, z: [[…]], x, y}` and
draws the 3D surface, `devices` expects `{scanning, found: […], devices: […]}` and lists them with
switches; look at the two built-in plugins for the exact shapes and the actions they take.

## daemon/plugin.py

```python
from printpi_daemon.plugins import PluginBase, PluginError


class Plugin(PluginBase):
    def start(self):
        # Called after load and after every settings change. self.settings has the
        # validated form values, self.state whatever save_state() kept last time.
        self.pin = int(self.settings["gpio_pin"])
        self.on = bool(self.state.get("on", False))
        self._apply()

    def stop(self):
        # Release hardware and threads; called before unload and before a restart.
        pass

    def handle(self, action, value):
        # A control from the UI. Runs on the bridge worker, so return quickly.
        if action == "set_on":
            self.on = bool(value)
            self.state["on"] = self.on
            self.save_state()
            self._apply()
            self.status_changed()
        else:
            raise PluginError(f"unknown action {action!r}")

    def status(self):
        # Shown next to the plugin; controls read their current value from here.
        return {"on": self.on}

    def _apply(self):
        level = self.on != bool(self.settings["invert"])
        ...
```

What the base class gives you:

| | |
|---|---|
| `self.settings`, `self.state`, `self.save_state()` | Settings from the form; state is your own dict, kept in Redis across restarts once you call `save_state()`. |
| `start()`, `stop()` | Lifecycle. `apply_settings()` by default stops, swaps the settings and starts again; override it if you can apply changes live. |
| `handle(action, value)` | A control was used. Raise `PluginError` with a readable message for anything wrong; the UI shows it. |
| `status()` | A dict the UI polls with the heartbeat (every 3 s). Call `self.status_changed()` when it has news and the UI gets it at once. |
| `send_gcode(command, timeout=None)` | Sends one line, waits for the `ok`, returns the reply lines. Raises when no printer is connected. |
| `on_event(event, payload)` | Something happened, see the events below. Runs on the host's event thread, so it may take a moment. |
| `on_printer_state(state)` | Every state change, the same dict the web app sees: `connection`, `status`, `temperatures`, `job`, … |
| `on_serial_line(direction, line)` | Every line on the wire (`"tx"` or `"rx"`). Runs on the printer's reader thread, so only look at the line and hand work to your own thread. |
| `pause_print()`, `resume_print()`, `cancel_print()` | Control the running print like the buttons do. The request is queued; the outcome arrives as `print_paused`, `print_resumed` or `print_cancelled`. |
| `notify(message, level="info", title=None)` | A toast in the UI (and on the touch panel). Levels are `info`, `success`, `warning`, `error`. |
| `connect_printer()`, `disconnect_printer()`, `printer_ports()`, `last_connection()` | Drive the connection, for plugins that power the printer. |

Two rules about threads. `handle()` runs on the bridge worker, the same thread that executes
G-code commands from the UI; anything that takes longer than a moment (a probing sequence, a
network scan) belongs on a thread of your own. `send_gcode()` blocks until the printer answers,
so a sequence of moves also belongs on your thread, never in `on_serial_line()`.

Plugins run inside the daemon process with its permissions. On the Pi that is the user the daemon
runs as, with the `dialout`, `video` and `kmem` groups the installer gives it.

## Events

`on_event(event, payload)` gets every one of these, in order, on a thread of the host's own:

| Event | Payload |
|---|---|
| `connected` | `port`, `baud`, `firmware` (the M115 name) |
| `disconnected` | `error`: the message when the connection was lost, `null` after a normal disconnect |
| `printer_error` | `message` |
| `print_started` | the job: `id`, `name`, `file_id`, `state`, `progress`, `layer`, `total_layers`, `elapsed`, `remaining`, `error` |
| `print_paused`, `print_resumed` | the job |
| `print_finished`, `print_cancelled` | the job |
| `print_failed` | the job, `error` says why |
| `layer_changed` | the job, with the new `layer` |
| `filament_loaded` | `spool`: the spool from PrintPi's inventory as `{id, name, material, color}`, or null |
| `filament_unloaded` | `spool`: null |

The same events go out on the Redis channel `printpi:events` as `{"type": "event", "event": …}`
for anything outside the daemon that wants them. The `webhook` plugin is the smallest example
of a consumer, `tapo-plug` uses `print_finished` and `print_started` for its auto-off.

## The printer's light and power switch

Two status keys have a meaning for the whole app. A plugin whose `status()` carries

```python
"printer_light": {"name": "LED strip", "on": True, "color": "#ffaa00"}
```

becomes the light button in the status bar and on the touch panel, switched through the actions
`printer_light_on` and `printer_light_off`; with a `color` the button gets a colour picker that
sends `printer_light_color` with a hex value. A plugin whose status carries

```python
"printer_power": {"id": "plug-1", "name": "Printer", "on": True, "online": True}
```

becomes the power button, switched through `printer_power_on` and `printer_power_off`; switch
off should `disconnect_printer()` first. The manifest must list these action names under a
control's `actions` or the app will not forward them.

## Requirements

`daemon/requirements.txt` is installed with pip into the daemon's virtualenv the first time the
plugin loads and again when the file changes. Keep it small; the Pi installs it while the daemon
runs. Libraries that only exist on the Pi (GPIO, SPI) should be imported inside `start()` with a
fallback, so the plugin still loads on a development machine.

## Developing

Run the daemon against the simulated printer and the web app on your machine, see
[development.md](development.md). Put your plugin directory next to the built-in ones in
`plugins/` (or install it from a local git URL), enable it on the Plugins page, and the daemon
picks it up. After changing the manifest run `php artisan printpi:sync-plugins` in `app/`, after
changing the code bump `version` in the manifest or restart the daemon. The daemon log
(`journalctl -u printpi-daemon` on the Pi, stdout on the Mac) shows load errors, the plugin page
shows the last `PluginError`.

Actions can be tried without the UI:

```bash
curl -X POST http://localhost:8000/api/v1/plugins/<id>/actions \
  -H 'Content-Type: application/json' -H 'X-XSRF-TOKEN: …' --cookie '…' \
  -d '{"action": "set_on", "value": true}'
```

The answer is the plugin's status after the action.
