"""Tapo plug: TP-Link smart plugs on the local network, switched from the dashboard.

The plugin looks for plugs on its own, at start and every few minutes, so the page only
ever offers to add what is already there. Added plugs live in the plugin state with what
is needed to reach them again without a search; a plug that moved to another address is
found at the next scan. A plug keeps the name its app gave it in "name"; a name chosen in
PrintPi sits in "label" and wins in the status. One plug can be marked as the one that
powers the printer: it is reported as printer_power, switched with printer_power_on and
printer_power_off (off disconnects the printer first), and with auto_connect the printer
is connected as soon as its port shows up after the plug went on, however it was switched.
With auto_off the plug goes off a few minutes after a print has finished, unless a new one
has started by then.
Everything on the wire runs on one worker thread, handle() only queues work, so the
bridge worker never waits for a plug.
"""

from __future__ import annotations

import functools
import logging
import queue
import threading
import time

from printpi_daemon.plugins import PluginBase, PluginError

from .network import FakeNetwork, Found, KasaNetwork, PlugError, Reading

log = logging.getLogger("printpi.plugins.tapo")

SCAN_INTERVAL = 600.0  # a plug plugged in later shows up without a click
REFRESH_INTERVAL = 5.0  # state and power draw of the added plugs
STOP_TIMEOUT = 5.0
AUTO_CONNECT_TIMEOUT = 180.0  # a printer that has not enumerated its port by then is not coming
AUTO_CONNECT_POLL = 2.0
CONNECT_WAIT = 45.0  # one connect attempt, including the daemon's own connect timeout
CONNECT_RETRY = 5.0  # pause after an attempt that ended in an error, the firmware may still be booting
DISCONNECT_WAIT = 5.0
MINUTE = 60.0  # auto-off delay unit; tests shrink it


def _no_reading() -> dict:
    return {"online": None, "on": False, "power_w": None, "energy_today_kwh": None, "error": None}


def _device_and_name(value) -> tuple[str, str | None]:
    """add and rename take a plain device id or {"id", "name"}; the name is trimmed, empty means none."""
    if isinstance(value, dict):
        name = str(value.get("name") or "").strip()
        return str(value.get("id") or ""), name or None
    return str(value or ""), None


class Plugin(PluginBase):
    _network: KasaNetwork | FakeNetwork | None = None
    _thread: threading.Thread | None = None

    def start(self) -> None:
        self._network = self._open_network()
        self.state.setdefault("devices", [])
        self._lock = threading.Lock()
        self._found: dict[str, Found] = {}
        self._handles: dict[str, object] = {}
        self._readings: dict[str, dict] = {}
        self._scanning = False
        self._scanned_at: float | None = None
        self._last_scan = 0.0
        self._error: str | None = None
        self._printer_connection: str = "offline"
        self._state_seq = 0  # counts printer state updates, so a connect attempt can be told from a stale error
        self._connecting_seq = -1
        self._printer_plug_on: bool | None = None
        self._auto_connect_thread: threading.Thread | None = None
        self._auto_off_timer: threading.Timer | None = None
        self._stop = threading.Event()
        self._jobs: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._work, name="tapo-plug", daemon=True)
        self._thread.start()
        self._jobs.put(self._scan)
        self._jobs.put(self._refresh)

    def stop(self) -> None:
        self._cancel_auto_off()
        network, self._network = self._network, None
        if self._thread is not None:
            self._stop.set()
            self._jobs.put(None)
        if network is not None:
            network.shutdown()  # cancels a running scan, so the worker can end
        if self._thread is not None:
            self._thread.join(timeout=STOP_TIMEOUT)
            self._thread = None

    def handle(self, action: str, value) -> None:
        if action == "scan":
            if self._scanning:
                raise PluginError("a scan is already running")
            self._jobs.put(self._scan)
        elif action == "add":
            self._add(*_device_and_name(value))
        elif action == "rename":
            self._rename(*_device_and_name(value))
        elif action == "remove":
            self._remove(str(value or ""))
        elif action in ("turn_on", "turn_off"):
            device_id = str(value or "")
            if self._device(device_id) is None:
                raise PluginError(f"no plug with id {device_id!r} is added")
            self._jobs.put(functools.partial(self._set_power, device_id, action == "turn_on"))
        elif action == "set_printer":
            self._set_printer(str(value or ""))
        elif action in ("printer_power_on", "printer_power_off"):
            device_id = self._printer_device_id()
            if device_id is None:
                raise PluginError("no plug is marked as powering the printer")
            self._jobs.put(functools.partial(self._power_printer, device_id, action == "printer_power_on"))
        else:
            raise PluginError(f"unknown action {action!r}")

    def on_printer_state(self, state: dict) -> None:
        connection = str(state.get("connection") or "offline")
        self._printer_connection = connection
        self._state_seq += 1
        if connection == "connecting":
            self._connecting_seq = self._state_seq

    def on_event(self, event: str, payload: dict) -> None:
        """A finished print starts the auto-off countdown; a new print stops it."""
        if event == "print_started":
            self._cancel_auto_off()
        elif event == "print_finished" and self.settings.get("auto_off"):
            device_id = self._printer_device_id()
            if device_id is None:
                return
            self._cancel_auto_off()
            delay = max(0, int(self.settings.get("auto_off_minutes") or 0)) * MINUTE
            self._auto_off_timer = threading.Timer(delay, self._jobs.put, args=(functools.partial(self._auto_off, device_id),))
            self._auto_off_timer.daemon = True
            self._auto_off_timer.start()

    def status(self) -> dict:
        with self._lock:
            devices = [dict(device) for device in self.state.get("devices", [])]
            readings = {device_id: dict(reading) for device_id, reading in self._readings.items()}
            found = list(self._found.values())
            printer_id = self.state.get("printer_device")
        added = {device["id"] for device in devices}
        printer = next((device for device in devices if device["id"] == printer_id), None)
        printer_reading = readings.get(printer_id, _no_reading()) if printer else None
        return {
            "printer_power": {
                "id": printer["id"], "name": printer.get("label") or printer["name"],
                "on": bool(printer_reading["on"]), "online": printer_reading["online"],
                "power_w": printer_reading["power_w"],
            } if printer else None,
            "plugs": {
                "scanning": self._scanning,
                "scanned_at": self._scanned_at,
                "error": self._error,
                "signed_in": bool(self._network and self._network.signed_in),
                "found": [
                    {"id": entry.id, "name": entry.name, "model": entry.model, "host": entry.host, "needs_auth": entry.needs_auth}
                    for entry in found if entry.id not in added
                ],
                "devices": [
                    {
                        "id": device["id"], "name": device.get("label") or device["name"], "plug_name": device["name"],
                        "model": device["model"], "host": device["host"], "printer": device["id"] == printer_id,
                        **readings.get(device["id"], _no_reading()),
                    }
                    for device in devices
                ],
            },
        }

    # ---- actions, on the bridge worker ------------------------------------------------

    def _add(self, device_id: str, label: str | None = None) -> None:
        entry = self._found.get(device_id)
        if entry is None:
            raise PluginError(f"no plug with id {device_id!r} was found")
        if entry.needs_auth:
            raise PluginError("sign in with the TP-Link account first")
        with self._lock:
            if self._device(device_id) is not None:
                raise PluginError(f"{entry.name or entry.model} is already added")
            device = {
                "id": entry.id, "name": entry.name or entry.model, "model": entry.model,
                "host": entry.host, "mac": entry.mac, "connection": dict(entry.connection),
            }
            if label and label != device["name"]:
                device["label"] = label
            self.state["devices"].append(device)
            self.save_state()
        self._jobs.put(self._refresh)

    def _rename(self, device_id: str, label: str | None) -> None:
        """An empty name goes back to the name the plug's own app gave it."""
        with self._lock:
            device = self._device(device_id)
            if device is None:
                raise PluginError(f"no plug with id {device_id!r} is added")
            if label and label != device["name"]:
                device["label"] = label
            else:
                device.pop("label", None)
            self.save_state()
        self.status_changed()

    def _remove(self, device_id: str) -> None:
        with self._lock:
            device = self._device(device_id)
            if device is None:
                raise PluginError(f"no plug with id {device_id!r} is added")
            self.state["devices"].remove(device)
            self._readings.pop(device_id, None)
            if self.state.get("printer_device") == device_id:
                self.state.pop("printer_device", None)
                self._printer_plug_on = None
            self.save_state()
        self._jobs.put(functools.partial(self._drop_handle, device_id))

    def _set_printer(self, device_id: str) -> None:
        """Mark the plug that powers the printer; an empty id clears the mark."""
        with self._lock:
            if device_id:
                if self._device(device_id) is None:
                    raise PluginError(f"no plug with id {device_id!r} is added")
                self.state["printer_device"] = device_id
                self._printer_plug_on = self._readings.get(device_id, {}).get("on") if device_id in self._readings else None
            else:
                self.state.pop("printer_device", None)
                self._printer_plug_on = None
            self.save_state()
        self.status_changed()

    def _device(self, device_id: str) -> dict | None:
        return next((device for device in self.state.get("devices", []) if device["id"] == device_id), None)

    def _printer_device_id(self) -> str | None:
        device_id = self.state.get("printer_device")
        return device_id if device_id and self._device(device_id) is not None else None

    @property
    def _auto_connect(self) -> bool:
        return bool(self.settings.get("auto_connect", True))

    # ---- the worker thread ----------------------------------------------------------------

    def _work(self) -> None:
        while not self._stop.is_set():
            try:
                job = self._jobs.get(timeout=REFRESH_INTERVAL)
            except queue.Empty:
                job = self._tick
            if job is None:
                return
            try:
                job()
            except Exception:  # noqa: BLE001 - one failed job must not end the worker
                log.exception("tapo-plug job failed")

    def _tick(self) -> None:
        if time.monotonic() - self._last_scan >= SCAN_INTERVAL:
            self._scan()
        self._refresh()

    def _scan(self) -> None:
        network = self._network
        if network is None:
            return
        self._scanning, self._error = True, None
        self.status_changed()
        try:
            found = network.discover()
            with self._lock:
                self._found = {entry.id: entry for entry in found}
            self._reconcile(found)
            if any(entry.needs_auth for entry in found):
                self._error = ("Sign in with the TP-Link account to use the Tapo plugs" if not network.signed_in
                               else "TP-Link account sign-in failed")
        except PlugError as exc:
            self._error = str(exc)
        finally:
            self._scanning = False
            self._last_scan = time.monotonic()
            self._scanned_at = time.time()
            self.status_changed()

    def _reconcile(self, found: list[Found]) -> None:
        """A plug that got a new address or name from its app is followed there."""
        by_id = {entry.id: entry for entry in found}
        changed = False
        with self._lock:
            for device in self.state.get("devices", []):
                entry = by_id.get(device["id"])
                if entry is None:
                    continue
                if entry.host != device["host"] or entry.connection != device.get("connection"):
                    device["host"], device["connection"] = entry.host, dict(entry.connection)
                    self._jobs.put(functools.partial(self._drop_handle, device["id"]))
                    changed = True
                if entry.name and entry.name != device["name"]:
                    device["name"] = entry.name
                    changed = True
            if changed:
                self.save_state()
                self._jobs.put(self._refresh)

    def _refresh(self) -> None:
        for device in list(self.state.get("devices", [])):
            if self._stop.is_set():
                return
            self._read(device)
        self.status_changed()

    def _read(self, device: dict) -> None:
        network = self._network
        if network is None:
            return
        device_id = device["id"]
        try:
            handle = self._handles.get(device_id)
            if handle is None:
                handle = network.open(device["host"], device["connection"])
                self._handles[device_id] = handle
            self._record(device_id, network.read(handle))
        except PlugError as exc:
            self._drop_handle(device_id)
            self._record(device_id, None, error=str(exc))

    def _set_power(self, device_id: str, on: bool) -> bool:
        network, device = self._network, self._device(device_id)
        if network is None or device is None:
            return False
        try:
            handle = self._handles.get(device_id)
            if handle is None:
                handle = network.open(device["host"], device["connection"])
                self._handles[device_id] = handle
            self._record(device_id, network.set_power(handle, on))
            done = True
        except PlugError as exc:
            self._drop_handle(device_id)
            self._record(device_id, None, error=str(exc))
            done = False
        self.status_changed()
        return done

    def _power_printer(self, device_id: str, on: bool) -> None:
        """Off closes the serial port first, so the printer is not cut off mid-command."""
        if not on and self._printer_connection == "connected":
            self.disconnect_printer()
            self._wait_for_connection(lambda: self._printer_connection != "connected", DISCONNECT_WAIT)
        if self._set_power(device_id, on) and on and self._auto_connect:
            self._start_auto_connect()

    def _cancel_auto_off(self) -> None:
        timer, self._auto_off_timer = self._auto_off_timer, None
        if timer is not None:
            timer.cancel()

    def _auto_off(self, device_id: str) -> None:
        device = self._device(device_id)
        if device is None or self._stop.is_set():
            return
        self._power_printer(device_id, False)
        self.notify(f"{device.get('label') or device['name']} switched off, the print is done", "info", "Tapo Plug")

    def _start_auto_connect(self) -> None:
        thread = self._auto_connect_thread
        if thread is not None and thread.is_alive():
            return
        self._auto_connect_thread = threading.Thread(target=self._auto_connect_printer, name="tapo-plug-connect", daemon=True)
        self._auto_connect_thread.start()

    def _auto_connect_printer(self) -> None:
        """Wait for the printer's port to enumerate after power-on, then connect once it is there.

        An attempt that ends in an error (the firmware was not ready yet) is repeated after a
        pause until the deadline.
        """
        deadline = time.monotonic() + AUTO_CONNECT_TIMEOUT
        target = self.last_connection()
        port = target.get("port") if target else None
        log.info("tapo-plug: printer plug is on, waiting for %s", port or "a connect target")
        while port and not self._stop.is_set() and time.monotonic() < deadline:
            if self._printer_connection == "connected":
                log.info("tapo-plug: printer is connected")
                return
            if port in self.printer_ports():
                log.info("tapo-plug: %s is there, connecting", port)
                mark = self._state_seq
                try:
                    self.connect_printer()
                except PluginError as exc:
                    log.warning("tapo-plug could not ask for a connect: %s", exc)
                    return
                if self._await_connect_attempt(mark):
                    log.info("tapo-plug: printer is connected")
                    return
                self._stop.wait(CONNECT_RETRY)
                continue
            self._stop.wait(AUTO_CONNECT_POLL)
        log.warning("tapo-plug: gave up connecting the printer")

    def _await_connect_attempt(self, mark: int) -> bool:
        """True once the bridge reports connected; False when the attempt that started after
        state update `mark` ended in an error, or nothing happened in time. A port that cannot
        be opened goes from connecting to error within milliseconds, hence the sequence numbers
        instead of watching for the connecting state."""
        deadline = time.monotonic() + CONNECT_WAIT
        while not self._stop.is_set() and time.monotonic() < deadline:
            connection = self._printer_connection
            if connection == "connected":
                return True
            if self._connecting_seq > mark and connection in ("error", "offline"):
                return False
            self._stop.wait(0.1)
        return self._printer_connection == "connected"

    def _wait_for_connection(self, condition, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while not self._stop.is_set() and time.monotonic() < deadline:
            if condition():
                return True
            self._stop.wait(0.1)
        return condition()

    def _record(self, device_id: str, reading: Reading | None, error: str | None = None) -> None:
        with self._lock:
            if reading is None:
                previous = self._readings.get(device_id, _no_reading())
                self._readings[device_id] = {**previous, "online": False, "error": error}
                return
            self._readings[device_id] = {
                "online": True, "on": reading.on, "power_w": reading.power_w,
                "energy_today_kwh": reading.energy_today_kwh, "error": None,
            }
            device = self._device(device_id)
            if device is not None and reading.name and reading.name != device["name"]:
                device["name"] = reading.name
                self.save_state()
            printer_plug = device_id == self.state.get("printer_device")
            switched_on = printer_plug and self._printer_plug_on is False and reading.on
            if printer_plug:
                self._printer_plug_on = reading.on
        # The plug went on from its button or its app: the printer is booting, meet it at the port.
        if switched_on and self._auto_connect and self._printer_connection != "connected":
            self._start_auto_connect()

    def _drop_handle(self, device_id: str) -> None:
        handle = self._handles.pop(device_id, None)
        if handle is not None and self._network is not None:
            self._network.close(handle)

    def _open_network(self):
        username = str(self.settings.get("username") or "").strip()
        password = str(self.settings.get("password") or "")
        if self.settings.get("driver") == "fake":
            return FakeNetwork(username, password)
        try:
            return KasaNetwork(username, password)
        except ImportError as exc:
            raise PluginError(f"{exc}; the plugin requirements are not installed") from exc
