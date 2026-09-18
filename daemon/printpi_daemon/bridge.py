"""Redis bridge between the daemon and the Laravel app.

  printpi:state      key with the latest state as JSON, and a channel that gets
                     every state change; "job" carries the print job (see job.py)
                     or null, "filament" the filament walkthrough (see filament.py) or null
  printpi:connection key with the last connect target: {"port", "baud"}
  printpi:ports      key with the serial ports the daemon can see, refreshed with
                     the heartbeat, so the UI can offer a printer to connect to
  printpi:cameras    key with the USB cameras the daemon can see
  printpi:system     key with host statistics (load, CPU utilisation, memory, disk, CPU temperature)
  printpi:system:history  list with one [unix seconds, cpu %, memory %] point per 30 s,
                     capped at 24 h, for the usage chart on the settings page
  printpi:camera     key with the state of the camera stream (running, device, error)
  printpi:camera:device  key with the camera the user picked; the stream is started
                     again after a daemon restart
  printpi:serial     channel with every line on the wire: {"dir": "rx"|"tx", "line": ...}
  printpi:serial:log list with the last few hundred of those lines, for a terminal
                     view that polls instead of subscribing
  printpi:events     channel for command results and errors, plus every plugin event as
                     {"type": "event", "event": "print_finished", ...payload} (see plugins.EVENTS)
  printpi:notifications  list with the last notifications plugins raised for the UI:
                     {"id", "at", "level", "title", "message", "plugin"}; the app shows new ones as toasts
  printpi:plugins    key the app writes with the enabled plugins as JSON:
                     [{"id", "path", "version", "settings"}]; the daemon loads
                     daemon/plugin.py from each path (see plugins.py)
  printpi:plugins:status  key with the state of every loaded plugin, refreshed
                     with the heartbeat, after every plugin action and whenever
                     a plugin reports a change (progress of a bed probe)
  printpi:plugins:state   hash with per-plugin state the daemon keeps across restarts
  printpi:plugins:requirements  hash with the requirements.txt hash pip last installed
  printpi:firmware   key with the state of the printer firmware update (see firmware.py),
                     refreshed with the heartbeat and on every change
  printpi:firmware:files  key with the files on the printer's SD card or USB drive,
                     written when the app asks for a listing
  printpi:commands   channel the app publishes commands to, as JSON:
                       {"type": "gcode", "command": "G28"}
                       {"type": "connect", "port": "/dev/ttyACM0", "baud": 115200}
                       {"type": "disconnect"} | {"type": "emergency_stop"}
                       {"type": "camera_start", "device": "/dev/video0"} | {"type": "camera_stop"}
                       {"type": "plugins_sync"} after the app changed printpi:plugins
                       {"type": "plugin_action", "id": "led-strip", "action": "set_color", "value": "#ff8800"}
                       {"type": "print_start", "path": "/.../part.gcode", "name": "part.gcode",
                        "file_id": 3, "estimated_seconds": 5025, "camera_url": "http://.../stream",
                        "bed": {"x": 250, "y": 210, "z": 220, "centered": false},
                        "timelapse": {"enabled": true, "gif": true, "mp4": true},
                        "cancel_gcode": ["M104 S0", "M140 S0"]}
                       (camera_url feeds the timelapse when the daemon runs no ustreamer itself,
                        bed places the park position of a pause on non-Prusa firmware, timelapse
                        says whether to record at all and which files to make, cancel_gcode
                        replaces the built-in script after a cancel; all optional)
                       {"type": "print_pause"} | {"type": "print_resume"} | {"type": "print_cancel"}
                       {"type": "print_restart"} prints the last job again
                       {"type": "filament_start", "action": "load"|"unload"|"change",
                        "spool": {"id": 3, "name": "Galaxy Black", "material": "PLA", "color": "#26262e"},
                        "material": "PLA", "nozzle": 215, "unload_nozzle": 230,
                        "moves": {"load": [[30, 360], [50, 1500]], "purge": [27, 180], "unload": [[8, 995], ...]}}
                       (spool and material for the record and the display, nozzle the temperature of the
                        filament going in, unload_nozzle of the one coming out, moves the profile's
                        [mm, mm/min] lists; all but action optional)
                       {"type": "filament_continue"} after the user inserted or pulled the filament
                       {"type": "filament_answer", "answer": "yes"|"purge"} to the colour check
                       {"type": "filament_cancel"}
                       {"type": "firmware_files"} lists the printer's drive into printpi:firmware:files
                       {"type": "firmware_flash", "method": "buddy"|"avrdude"|"restart", "file": ...,
                        "mcu": "atmega2560", "programmer": "wiring", "baud": 115200}
                       (file is a name on the printer's drive for buddy, a path on this host for avrdude)
  printpi:jobs:done  list with a record per ended print job (the job fields plus
                     "timelapse": {"gif", "mp4", "cover", "frames", "error"} or null);
                     the app drains it into its print history
  printpi:filament:done  list with {"event": "loaded"|"unloaded", "spool", "at"} per filament
                     the walkthrough put in or took out; the app drains it into its inventory
  printpi:heartbeat  key refreshed every few seconds while the daemon runs

The daemon does not connect on its own in bridge mode: the user picks a port in
the UI and sends "connect", which may name a different port than the daemon was
started with.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
import uuid
from typing import Callable

import redis
import serial.tools.list_ports

from .camera import CameraError, CameraStreamer, list_cameras
from .filament import FilamentError, FilamentRunner, FilamentState
from .firmware import FirmwareError, FirmwareUpdater, list_files
from .job import ACTIVE_STATES, JobError, JobState, SerialJobRunner
from .plugins import PluginError, PluginHost
from .printer import Printer, PrinterError
from .state import PrinterState
from .system import HISTORY_SIZE, SystemMonitor
from .timelapse import TimelapseRecorder

log = logging.getLogger("printpi.bridge")

STATE_KEY = "printpi:state"
STATE_CHANNEL = "printpi:state"
PORTS_KEY = "printpi:ports"
SYSTEM_KEY = "printpi:system"
SYSTEM_HISTORY_KEY = "printpi:system:history"
CAMERAS_KEY = "printpi:cameras"
CAMERA_KEY = "printpi:camera"
CAMERA_DEVICE_KEY = "printpi:camera:device"
CONNECTION_KEY = "printpi:connection"
PLUGINS_KEY = "printpi:plugins"
PLUGIN_STATUS_KEY = "printpi:plugins:status"
PLUGIN_STATE_KEY = "printpi:plugins:state"
PLUGIN_REQUIREMENTS_KEY = "printpi:plugins:requirements"
FIRMWARE_KEY = "printpi:firmware"
FIRMWARE_FILES_KEY = "printpi:firmware:files"
SERIAL_CHANNEL = "printpi:serial"
SERIAL_LOG_KEY = "printpi:serial:log"
SERIAL_LOG_SIZE = 500
EVENTS_CHANNEL = "printpi:events"
COMMAND_CHANNEL = "printpi:commands"
HEARTBEAT_KEY = "printpi:heartbeat"
JOBS_DONE_KEY = "printpi:jobs:done"
JOBS_DONE_SIZE = 100
FILAMENT_DONE_KEY = "printpi:filament:done"
FILAMENT_DONE_SIZE = 50
NOTIFICATIONS_KEY = "printpi:notifications"
NOTIFICATIONS_SIZE = 100
NOTIFICATION_LEVELS = ("info", "success", "warning", "error")
# Lists the app reads from the tail; the publisher appends and trims them.
LIST_KEYS = {JOBS_DONE_KEY: JOBS_DONE_SIZE, NOTIFICATIONS_KEY: NOTIFICATIONS_SIZE, FILAMENT_DONE_KEY: FILAMENT_DONE_SIZE}
# Keys the app polls; the publisher sets them instead of publishing on a channel.
POLLED_KEYS = (PLUGIN_STATUS_KEY, FIRMWARE_KEY, FIRMWARE_FILES_KEY)

FAKE_PORT = "fake://"
# (was the previous state active?, the new state) -> the event plugins get
JOB_EVENTS = {
    (True, "paused"): "print_paused",
    (True, "printing"): "print_resumed",
    (True, "finished"): "print_finished",
    (True, "cancelled"): "print_cancelled",
    (True, "error"): "print_failed",
}
JOB_EVENT_FIELDS = ("id", "name", "file_id", "state", "progress", "layer", "total_layers", "elapsed", "remaining", "error")


def list_ports() -> list[dict[str, str]]:
    """Serial ports a user could pick, plus the udev alias and the fake printer."""
    ports = [
        {"device": port.device, "description": port.description or "", "hwid": port.hwid or ""}
        for port in serial.tools.list_ports.comports()
    ]
    ports.sort(key=lambda entry: entry["device"])
    if os.path.exists("/dev/printer"):
        ports.insert(0, {"device": "/dev/printer", "description": "udev alias for the printer", "hwid": ""})
    ports.append({"device": FAKE_PORT, "description": "Simulated printer", "hwid": ""})
    return ports


def printer_power_watts(statuses: dict[str, dict]) -> float | None:
    """The power draw of the printer's plug, from the first running plugin that reports one."""
    for entry in statuses.values():
        power = entry.get("status", {}).get("printer_power") if entry.get("state") == "running" else None
        if isinstance(power, dict) and isinstance(power.get("power_w"), (int, float)):
            return float(power["power_w"])
    return None


class RedisBridge:
    def __init__(self, url: str, printer: Printer, *, timelapse_dir: str | None = None) -> None:
        self.redis = redis.Redis.from_url(url, decode_responses=True)
        self.printer = printer
        self._serial_options = {
            "serial_log": printer.serial_log,
            "temperature_interval": printer.temperature_interval,
            "ok_timeout": printer.ok_timeout,
            "probe_timeout": printer.probe_timeout,
            "connect_timeout": printer.connect_timeout,
        }
        self._attach(printer)
        self.camera = CameraStreamer()
        self.system = SystemMonitor()
        self.timelapse = TimelapseRecorder(timelapse_dir)
        self.plugins = PluginHost(
            load_state=self._load_plugin_state,
            save_state=self._save_plugin_state,
            on_requirements_installed=self._remember_requirements,
            # Looked up per call: "connect" may replace self.printer with one for another port.
            send_gcode=self._send_manual_gcode,
            status_changed=self._publish_plugin_status,
            printer_control=self._plugin_printer_control,
            printer_ports=lambda: [entry["device"] for entry in list_ports()],
            last_connection=self._connection_target,
            print_control=self._plugin_print_control,
            notify=self._notify,
        )
        self._last_connection: dict | None = None
        # The runner asks for the printer on every start, since connect may replace it.
        self.jobs = SerialJobRunner(lambda: self.printer, on_state=self._on_job_state,
                                    on_part_finished=lambda job: self.timelapse.capture_final())
        self.filament = FilamentRunner(lambda: self.printer, on_state=self._on_filament_state,
                                       on_record=self._on_filament_record)
        # Connect and disconnect take their turn on the command worker like the UI's commands do.
        self.firmware = FirmwareUpdater(
            printer=lambda: self.printer,
            connect=lambda: self._run_on_worker(lambda: self._connect(**self._connection_target())),
            disconnect=lambda: self._run_on_worker(self._disconnect_printer),
            on_status=lambda status: self._outbox.put((FIRMWARE_KEY, json.dumps(status))),
        )
        self._job_seen: tuple[str, int, str] | None = None  # id, layer and state of the last job update handled
        self._connection_seen: tuple[str, str | None] | None = None  # connection and last_error of the last state
        self._events: queue.Queue[tuple[str, dict] | None] = queue.Queue()
        self._job_camera_url: str | None = None
        self._job_timelapse: dict = {"enabled": True, "gif": True, "mp4": True}
        self._power_sample: tuple[str, float, float] | None = None  # job id, monotonic time, watts
        self._outbox: queue.Queue[tuple[str, str]] = queue.Queue()
        self._commands: queue.Queue[dict] = queue.Queue()
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        self.redis.ping()
        for target, name in (
            (self._publisher, "bridge-publisher"),
            (self._listener, "bridge-listener"),
            (self._worker, "bridge-worker"),
            (self._heartbeat, "bridge-heartbeat"),
            (self._dispatch_events, "bridge-events"),
        ):
            thread = threading.Thread(target=target, name=name, daemon=True)
            thread.start()
            self._threads.append(thread)
        self._on_state(self.printer.state.snapshot())
        self._restore_connection()
        self._restore_camera()
        self._restore_plugins()
        log.info("redis bridge started, timelapses go to %s", self.timelapse.root)

    def stop(self) -> None:
        self._stop.set()
        self._commands.put({"type": "_quit"})
        self._outbox.put(("", ""))
        self._events.put(None)
        self.jobs.stop()
        self.filament.stop()
        self.camera.stop()
        self.plugins.stop_all()

    def _restore_connection(self) -> None:
        """The last connect target, so a plugin can reopen the printer after a daemon restart."""
        try:
            raw = self.redis.get(CONNECTION_KEY)
        except redis.RedisError:
            return
        if raw:
            try:
                target = json.loads(raw)
                self._last_connection = {"port": str(target["port"]), "baud": int(target["baud"])}
            except (ValueError, KeyError, TypeError):
                log.warning("ignoring malformed %s", CONNECTION_KEY)

    def _connection_target(self) -> dict:
        """The last connect target, else the port the daemon was started with (/dev/printer on the Pi)."""
        if self._last_connection:
            return dict(self._last_connection)
        return {"port": self.printer.port_url, "baud": self.printer.baudrate}

    def _remember_connection(self, port: str, baud: int) -> None:
        self._last_connection = {"port": port, "baud": baud}
        try:
            self.redis.set(CONNECTION_KEY, json.dumps(self._last_connection))
        except redis.RedisError as exc:
            log.warning("could not store the connection target: %s", type(exc).__name__)

    def _plugin_printer_control(self, action: str) -> None:
        """Plugins queue connect and disconnect like the UI does, so the worker keeps the order."""
        if action == "connect":
            self._commands.put({"type": "reconnect"})
        elif action == "disconnect":
            self._commands.put({"type": "disconnect"})
        else:
            raise PluginError(f"unknown printer control {action!r}")

    def _plugin_print_control(self, action: str) -> None:
        """Pause, resume and cancel from a plugin take their turn on the worker like the UI's buttons."""
        if action not in ("pause", "resume", "cancel"):
            raise PluginError(f"unknown print control {action!r}")
        self._commands.put({"type": f"print_{action}"})

    def _notify(self, plugin_id: str, level: str, message: str, title: str | None) -> None:
        """A plugin's message for the user, appended to the list the app turns into toasts."""
        record = {
            "id": uuid.uuid4().hex[:12],
            "at": time.time(),
            "level": level if level in NOTIFICATION_LEVELS else "info",
            "title": str(title) if title else None,
            "message": str(message),
            "plugin": plugin_id,
        }
        self._outbox.put((NOTIFICATIONS_KEY, json.dumps(record)))

    def _emit(self, event: str, **payload) -> None:
        """An event for the plugins (on their own thread) and, for anyone listening, the events channel."""
        self._events.put((event, payload))
        self._event("event", event=event, **payload)

    def _dispatch_events(self) -> None:
        while True:
            item = self._events.get()
            if item is None:
                return
            self.plugins.notify_event(*item)

    def _restore_camera(self) -> None:
        """Start the remembered camera again after a daemon restart."""
        try:
            device = self.redis.get(CAMERA_DEVICE_KEY)
        except redis.RedisError:
            return
        if not device or self.camera.status()["running"] or not self.camera.available():
            return
        try:
            self.camera.start(device)
        except CameraError as exc:
            log.warning("could not restore camera %s: %s", device, exc)

    # ---- plugins -----------------------------------------------------------------------

    def _restore_plugins(self) -> None:
        """Remember which requirements pip already installed, then load what the app enabled."""
        try:
            installed = self.redis.hgetall(PLUGIN_REQUIREMENTS_KEY)
        except redis.RedisError as exc:
            log.warning("could not read plugin requirements: %s", exc)
            installed = {}
        self.plugins._requirements_installed.update(installed)
        self._sync_plugins()

    def _sync_plugins(self) -> None:
        """Loading may pip-install requirements, so it runs off the command worker."""
        threading.Thread(target=self._sync_plugins_now, name="plugin-sync", daemon=True).start()

    def _sync_plugins_now(self) -> None:
        try:
            raw = self.redis.get(PLUGINS_KEY)
            specs = json.loads(raw) if raw else []
        except (redis.RedisError, ValueError) as exc:
            log.warning("could not read plugin list: %s", exc)
            return
        self.plugins.sync(specs if isinstance(specs, list) else [])
        self._publish_plugin_status()
        self._event("plugins_synced", plugins=self.plugins.ids)

    def _publish_plugin_status(self) -> None:
        """Through the outbox, because plugins call this from the printer's reader thread."""
        self._outbox.put((PLUGIN_STATUS_KEY, json.dumps(self.plugins.statuses())))

    def _load_plugin_state(self, plugin_id: str) -> dict:
        try:
            raw = self.redis.hget(PLUGIN_STATE_KEY, plugin_id)
            state = json.loads(raw) if raw else {}
        except (redis.RedisError, ValueError) as exc:
            log.warning("could not load state of plugin %s: %s", plugin_id, exc)
            return {}
        return state if isinstance(state, dict) else {}

    def _save_plugin_state(self, plugin_id: str, state: dict) -> None:
        try:
            self.redis.hset(PLUGIN_STATE_KEY, plugin_id, json.dumps(state))
        except redis.RedisError as exc:
            log.warning("could not save state of plugin %s: %s", plugin_id, exc)

    def _remember_requirements(self, plugin_id: str, digest: str) -> None:
        try:
            self.redis.hset(PLUGIN_REQUIREMENTS_KEY, plugin_id, digest)
        except redis.RedisError as exc:
            log.warning("could not record requirements of plugin %s: %s", plugin_id, exc)

    # ---- printer -> redis ------------------------------------------------------------

    def _attach(self, printer: Printer) -> None:
        printer.on_state = self._on_state
        printer.on_line = self._on_line
        printer.on_action = lambda action: self.jobs.handle_action(action)

    def _on_state(self, state: PrinterState) -> None:
        data = state.to_dict()
        job = self.jobs.state
        data["job"] = job.to_dict() if job is not None else None
        filament = self.filament.state
        data["filament"] = filament.to_dict() if filament is not None else None
        self._outbox.put((STATE_CHANNEL, json.dumps(data)))
        self._track_connection(data)
        self.plugins.notify_printer_state(data)

    def _track_connection(self, data: dict) -> None:
        """Connection changes and new errors become events."""
        connection, error = str(data.get("connection")), data.get("last_error")
        previous, self._connection_seen = self._connection_seen, (connection, error)
        if previous is None:
            return
        if connection == "connected" and previous[0] != "connected":
            firmware = data.get("firmware") or {}
            self._emit("connected", port=data.get("port"), baud=data.get("baudrate"),
                       firmware=firmware.get("FIRMWARE_NAME") if isinstance(firmware, dict) else None)
        elif connection != "connected" and previous[0] == "connected":
            self._emit("disconnected", error=error if connection == "error" else None)
        if error and error != previous[1]:
            self._emit("printer_error", message=error)

    def _on_job_state(self, job: JobState) -> None:
        self._track_job(job)
        self._on_state(self.printer.state.snapshot())

    def _on_filament_state(self, state: FilamentState) -> None:
        self._on_state(self.printer.state.snapshot())

    def _on_filament_record(self, event: str, spool: dict | None) -> None:
        """What the walkthrough put in or took out, for the app's inventory and the plugins."""
        self._outbox.put((FILAMENT_DONE_KEY, json.dumps({"event": event, "spool": spool, "at": time.time()})))
        self._emit(f"filament_{event}", spool=spool)

    def _track_job(self, job: JobState) -> None:
        """Feed the timelapse from the job's progress and file its record once it has ended."""
        previous = self._job_seen
        self._job_seen = (job.id, job.layer, job.state)
        if previous is None or previous[0] != job.id:
            if job.active:
                self.timelapse.begin(job.id, self._timelapse_source() if self._job_timelapse["enabled"] else None)
                self._emit("print_started", **self._job_payload(job))
            return
        if job.state != previous[2]:
            event = JOB_EVENTS.get((previous[2] in ACTIVE_STATES, job.state))
            if event:
                self._emit(event, **self._job_payload(job))
        if job.active and job.layer != previous[1]:
            self.timelapse.capture()
            self._emit("layer_changed", **self._job_payload(job))
        elif not job.active and previous[2] in ACTIVE_STATES:
            # Runs on the print thread; assembling the movie takes a while.
            threading.Thread(target=self._file_job, args=(job,), name="job-record", daemon=True).start()

    @staticmethod
    def _job_payload(job: JobState) -> dict:
        data = job.to_dict()
        return {key: data.get(key) for key in JOB_EVENT_FIELDS}

    def _timelapse_source(self) -> str | None:
        """The daemon's own ustreamer when it runs, else the stream URL the app passed with the print."""
        return self.camera.snapshot_url() or self._job_camera_url

    def _file_job(self, job: JobState) -> None:
        record = job.to_dict()
        record["timelapse"] = self.timelapse.finish(gif=self._job_timelapse["gif"], mp4=self._job_timelapse["mp4"])
        self._outbox.put((JOBS_DONE_KEY, json.dumps(record)))
        self._event("print_recorded", id=job.id, name=job.name, state=job.state)

    def _meter_energy(self) -> None:
        """Integrate the power draw a plugin reports for the printer's plug into the running job."""
        job = self.jobs.state
        if job is None or not job.active:
            self._power_sample = None
            return
        watts = printer_power_watts(self.plugins.statuses())
        if watts is None:
            self._power_sample = None
            return
        now = time.monotonic()
        previous, self._power_sample = self._power_sample, (job.id, now, watts)
        if previous is not None and previous[0] == job.id:
            self.jobs.add_energy((previous[2] + watts) / 2 * (now - previous[1]) / 3600)

    def _on_line(self, direction: str, line: str) -> None:
        self._outbox.put((SERIAL_CHANNEL, json.dumps({"dir": direction, "line": line, "t": time.time()})))
        self.plugins.notify_serial_line(direction, line)

    def _publisher(self) -> None:
        while not self._stop.is_set():
            channel, payload = self._outbox.get()
            if not channel:
                continue
            try:
                pipe = self.redis.pipeline(transaction=False)
                if channel == STATE_CHANNEL:
                    pipe.set(STATE_KEY, payload)
                elif channel == SERIAL_CHANNEL:
                    pipe.rpush(SERIAL_LOG_KEY, payload)
                    pipe.ltrim(SERIAL_LOG_KEY, -SERIAL_LOG_SIZE, -1)
                if channel in POLLED_KEYS:
                    pipe.set(channel, payload)
                elif channel in LIST_KEYS:
                    pipe.rpush(channel, payload)  # a list the app reads, no channel
                    pipe.ltrim(channel, -LIST_KEYS[channel], -1)
                else:
                    pipe.publish(channel, payload)
                pipe.execute()
            except redis.RedisError as exc:
                log.warning("redis publish failed: %s", exc)
                time.sleep(1)

    def _heartbeat(self) -> None:
        while True:
            self._meter_energy()
            try:
                pipe = self.redis.pipeline(transaction=False)
                pipe.set(HEARTBEAT_KEY, str(time.time()), ex=10)
                pipe.set(PORTS_KEY, json.dumps(list_ports()))
                pipe.set(CAMERAS_KEY, json.dumps(list_cameras()))
                pipe.set(CAMERA_KEY, json.dumps(self.camera.status()))
                pipe.set(PLUGIN_STATUS_KEY, json.dumps(self.plugins.statuses()))
                pipe.set(FIRMWARE_KEY, json.dumps(self.firmware.status()))
                stats, point = self.system.sample()
                pipe.set(SYSTEM_KEY, json.dumps(stats))
                if point is not None:
                    pipe.rpush(SYSTEM_HISTORY_KEY, json.dumps(point))
                    pipe.ltrim(SYSTEM_HISTORY_KEY, -HISTORY_SIZE, -1)
                pipe.execute()
            except redis.RedisError as exc:
                log.warning("redis heartbeat failed: %s", exc)
            if self._stop.wait(3):
                return

    # ---- redis -> printer ------------------------------------------------------------

    def _listener(self) -> None:
        while not self._stop.is_set():
            try:
                pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
                pubsub.subscribe(COMMAND_CHANNEL)
                for message in pubsub.listen():
                    if self._stop.is_set():
                        break
                    try:
                        self._commands.put(json.loads(message["data"]))
                    except (TypeError, ValueError):
                        log.warning("ignoring malformed command")
            except redis.RedisError as exc:
                log.warning("redis subscribe failed: %s, retrying", exc)
                time.sleep(2)

    def _worker(self) -> None:
        while not self._stop.is_set():
            command = self._commands.get()
            if command.get("type") == "_quit":
                return
            try:
                self._execute(command)
            except (PrinterError, PluginError, JobError, FirmwareError, FilamentError) as exc:
                self._event("error", command=command, message=str(exc))
            except Exception as exc:  # noqa: BLE001 - keep the worker alive
                log.exception("command failed")
                self._event("error", command=command, message=str(exc))

    def _send_manual_gcode(self, command: str, timeout: float | None = None) -> list[str]:
        # Do not queue manual/plugin moves behind a blocking native dialog or
        # change heaters/modes between two stages of a filament walkthrough.
        if self.filament.active:
            raise PrinterError("cannot send manual commands while filament is being changed")
        return self.printer.send(command, timeout=timeout)

    def _execute(self, command: dict) -> None:
        kind = command.get("type")
        if kind == "gcode":
            response = self._send_manual_gcode(str(command.get("command", "")))
            self._event("gcode", command=command, response=response)
        elif kind == "connect":
            self._connect(str(command.get("port") or self.printer.port_url),
                          int(command.get("baud") or self.printer.baudrate))
        elif kind == "reconnect":
            self._connect(**self._connection_target())
        elif kind == "disconnect":
            self._disconnect_printer()
        elif kind == "emergency_stop":
            self.printer.emergency_stop()
            self._event("emergency_stop")
        elif kind == "camera_start":
            device = str(command.get("device") or "")
            try:
                self.camera.start(device, resolution=str(command.get("resolution") or "1280x720"))
            except CameraError as exc:
                self._event("error", command=command, message=str(exc))
                return
            self._remember_camera(device)
            self._event("camera_started", device=device)
        elif kind == "camera_stop":
            self.camera.stop()
            self._remember_camera(None)
            self._event("camera_stopped")
        elif kind == "print_start":
            if self.filament.active:
                raise JobError("cannot print while filament is being changed")
            estimate = command.get("estimated_seconds")
            self._job_camera_url = str(command.get("camera_url") or "") or None
            timelapse = command.get("timelapse") if isinstance(command.get("timelapse"), dict) else {}
            self._job_timelapse = {key: bool(timelapse.get(key, True)) for key in ("enabled", "gif", "mp4")}
            bed = command.get("bed")
            cancel_gcode = command.get("cancel_gcode")
            job = self.jobs.start(
                str(command.get("path") or ""),
                name=str(command.get("name") or "") or None,
                file_id=int(command["file_id"]) if command.get("file_id") is not None else None,
                estimated_seconds=int(estimate) if estimate is not None else None,
                bed=bed if isinstance(bed, dict) else None,
                cancel_gcode=[str(line) for line in cancel_gcode] if isinstance(cancel_gcode, list) else None,
            )
            self._event("print_started", name=job.name)
        elif kind == "print_pause":
            self.jobs.pause()
            self._event("print_paused")
        elif kind == "print_resume":
            self.jobs.resume()
            self._event("print_resumed")
        elif kind == "print_cancel":
            self.jobs.cancel()
            self._event("print_cancelled")
        elif kind == "print_restart":
            if self.filament.active:
                raise JobError("cannot print while filament is being changed")
            job = self.jobs.restart()
            self._event("print_started", name=job.name)
        elif kind == "filament_start":
            job = self.jobs.state
            if job is not None and job.active:
                raise FilamentError("cannot change filament while a print is active")
            if self.firmware.status().get("phase") in ("preparing", "flashing", "rebooting", "reconnecting"):
                raise FilamentError("cannot change filament while the firmware is being updated")
            nozzle, unload_nozzle = command.get("nozzle"), command.get("unload_nozzle")
            state = self.filament.start(
                str(command.get("action") or ""),
                spool=command.get("spool") if isinstance(command.get("spool"), dict) else None,
                material=str(command.get("material") or "") or None,
                nozzle=int(nozzle) if nozzle else None,
                unload_nozzle=int(unload_nozzle) if unload_nozzle else None,
                moves=command.get("moves") if isinstance(command.get("moves"), dict) else None,
            )
            self._event("filament_started", action=state.action, id=state.id)
        elif kind == "filament_continue":
            self.filament.proceed()
        elif kind == "filament_answer":
            self.filament.answer(str(command.get("answer") or ""))
        elif kind == "filament_cancel":
            self.filament.cancel()
            self._event("filament_cancelled")
        elif kind == "firmware_files":
            if self.filament.active:
                raise FirmwareError("cannot access the printer drive while filament is being changed")
            self._list_firmware_files()
        elif kind == "firmware_flash":
            if self.filament.active:
                raise FirmwareError("cannot update the firmware while filament is being changed")
            job = self.jobs.state
            if job is not None and job.active:
                raise FirmwareError("cannot update the firmware while a print is active")
            baud = command.get("baud")
            status = self.firmware.start(
                str(command.get("method") or ""),
                file=str(command.get("file") or "") or None,
                port=self._connection_target().get("port"),
                mcu=str(command.get("mcu") or "") or None,
                programmer=str(command.get("programmer") or "") or None,
                baud=int(baud) if baud else None,
            )
            self._event("firmware_flash", method=status["method"], file=status["file"])
        elif kind == "_call":
            command["fn"]()
        elif kind == "plugins_sync":
            self._sync_plugins()
        elif kind == "plugin_action":
            plugin_id = str(command.get("id") or "")
            status = self.plugins.action(plugin_id, str(command.get("action") or ""), command.get("value"))
            self._publish_plugin_status()
            self._event("plugin_action", id=plugin_id, action=command.get("action"), status=status)
        else:
            self._event("error", command=command, message=f"unknown command type {kind!r}")

    def _disconnect_printer(self) -> None:
        self.printer.disconnect()
        self._event("disconnected")

    def _run_on_worker(self, fn: Callable[[], None], timeout: float = 120.0) -> None:
        """Run fn on the command worker and wait for it; errors are raised here, not published."""
        done = threading.Event()
        failure: list[BaseException] = []

        def call() -> None:
            try:
                fn()
            except BaseException as exc:  # noqa: BLE001 - handed to the caller
                failure.append(exc)
            finally:
                done.set()

        self._commands.put({"type": "_call", "fn": call})
        if not done.wait(timeout):
            raise PrinterError("the daemon is busy with another command")
        if failure:
            raise failure[0]

    def _list_firmware_files(self) -> None:
        """The printer's drive listing, with the error in the key so the UI can show it."""
        payload: dict = {"files": [], "listed_at": time.time(), "error": None}
        try:
            payload["files"] = list_files(self.printer)
        except PrinterError as exc:
            payload["error"] = str(exc)
        self._outbox.put((FIRMWARE_FILES_KEY, json.dumps(payload)))
        if payload["error"]:
            raise PrinterError(payload["error"])

    def _connect(self, port: str, baud: int) -> None:
        current = self.printer
        same = current.port_url == port and current.baudrate == baud
        job = self.jobs.state
        if not same and job is not None and job.active:
            raise JobError("cannot change the printer port while a print is active")
        self._remember_connection(port, baud)
        if current.connected and same:
            self._event("connected", port=port, baud=baud)
            return
        if current.connected:
            current.disconnect()
        if not same:
            self.printer = Printer(port, baud, **self._serial_options)
            self._attach(self.printer)
        log.info("connecting to %s at %d baud", port, baud)
        self.printer.connect()
        self._event("connected", port=port, baud=baud)

    def _remember_camera(self, device: str | None) -> None:
        try:
            if device:
                self.redis.set(CAMERA_DEVICE_KEY, device)
            else:
                self.redis.delete(CAMERA_DEVICE_KEY)
        except redis.RedisError as exc:
            log.warning("could not store camera choice: %s", exc)
        try:
            self.redis.set(CAMERA_KEY, json.dumps(self.camera.status()))
        except redis.RedisError:
            pass

    def _event(self, kind: str, **fields) -> None:
        self._outbox.put((EVENTS_CHANNEL, json.dumps({"type": kind, "t": time.time(), **fields})))
