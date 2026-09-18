"""Daemon-side plugin host.

A plugin is a directory with a plugin.json manifest. The web app owns the
manifest, the install state and the settings; it writes the enabled plugins to
Redis (printpi:plugins) and the bridge hands that list to PluginHost.sync(),
which loads the daemon part of each plugin: daemon/plugin.py inside the plugin
directory, defining a class Plugin(PluginBase).

Plugins run inside the daemon process and can do whatever the daemon can: drive
GPIO, spawn processes, watch the printer state. Requirements listed in
daemon/requirements.txt are installed into the daemon's own environment once;
the file's hash is remembered so a restart does not run pip again.
"""

from __future__ import annotations

import hashlib
import importlib.util
import logging
import re
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

log = logging.getLogger("printpi.plugins")

MODULE_PREFIX = "printpi_plugin_"
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class PluginError(Exception):
    pass


SendGcode = Callable[[str, float | None], list[str]]


def _no_printer(command: str, timeout: float | None) -> list[str]:
    raise PluginError("no printer to send G-code to")


def _no_printer_control(action: str) -> None:
    raise PluginError("no printer link")


def _no_print_control(action: str) -> None:
    raise PluginError("no print job link")


def _no_notify(level: str, message: str, title: str | None) -> None:
    log.info("notification (%s) %s: %s", level, title or "", message)


# What on_event() receives, with the payload each carries.
EVENTS = {
    "connected": "port, baud, firmware",
    "disconnected": "error (the message when the connection was lost, else null)",
    "printer_error": "message",
    "print_started": "the job: id, name, file_id, state, progress, layer, total_layers, elapsed, remaining, error",
    "print_paused": "the job",
    "print_resumed": "the job",
    "print_finished": "the job",
    "print_cancelled": "the job",
    "print_failed": "the job, with error",
    "layer_changed": "the job, with the new layer and total_layers",
    "filament_loaded": "spool ({id, name, material, color} from PrintPi's inventory, or null)",
    "filament_unloaded": "spool (null)",
}


@dataclass
class PluginContext:
    """What a plugin gets from the host: its identity, settings, persistence and the printer."""

    id: str
    path: Path
    settings: dict
    state: dict
    save_state: Callable[[dict], None]
    send_gcode: SendGcode = _no_printer
    status_changed: Callable[[], None] = lambda: None
    printer_control: Callable[[str], None] = _no_printer_control
    printer_ports: Callable[[], list[str]] = lambda: []
    last_connection: Callable[[], dict | None] = lambda: None
    print_control: Callable[[str], None] = _no_print_control
    notify: Callable[[str, str, str | None], None] = _no_notify


class PluginBase:
    """Base class for the daemon part of a plugin.

    Settings come from the UI form the manifest describes and are validated by
    the app. State is whatever the plugin wants to keep across restarts, such as
    the last colour of an LED strip; call save_state() after changing it.
    """

    def __init__(self, context: PluginContext) -> None:
        self.context = context
        self.id = context.id
        self.settings = dict(context.settings)
        self.state = dict(context.state)

    def send_gcode(self, command: str, timeout: float | None = None) -> list[str]:
        """Send one command to the printer and wait for its ok; returns the reply lines.

        Blocks while the printer works and raises PrinterError when it is not
        connected, so long sequences belong on a thread of the plugin's own.
        """
        return self.context.send_gcode(command, timeout)

    def status_changed(self) -> None:
        """Tell the host that status() has news, so the UI sees it before the next heartbeat."""
        self.context.status_changed()

    def connect_printer(self) -> None:
        """Ask the bridge to reopen the port of the last connect; the result shows up in on_printer_state()."""
        self.context.printer_control("connect")

    def disconnect_printer(self) -> None:
        self.context.printer_control("disconnect")

    def printer_ports(self) -> list[str]:
        """Device paths of the serial ports the daemon can see right now."""
        return self.context.printer_ports()

    def last_connection(self) -> dict | None:
        """{"port", "baud"} of the last connect command, also across daemon restarts, or None."""
        return self.context.last_connection()

    def pause_print(self) -> None:
        """Pause the running print like the Pause button; the outcome arrives as an event."""
        self.context.print_control("pause")

    def resume_print(self) -> None:
        self.context.print_control("resume")

    def cancel_print(self) -> None:
        self.context.print_control("cancel")

    def notify(self, message: str, level: str = "info", title: str | None = None) -> None:
        """A notification in the UI; level is info, success, warning or error."""
        self.context.notify(level, message, title)

    def start(self) -> None:
        """Called once the plugin is loaded and again after every restart."""

    def stop(self) -> None:
        """Release hardware and threads; called before unload and restart."""

    def apply_settings(self, settings: dict) -> None:
        """New settings from the UI. The default restarts the plugin."""
        self.stop()
        self.settings = dict(settings)
        self.start()

    def handle(self, action: str, value: Any) -> None:
        """A control from the UI; raise PluginError for anything unsupported."""
        raise PluginError(f"unknown action {action!r}")

    def status(self) -> dict:
        """Shown in the UI next to the plugin; control values are read from here."""
        return {}

    def on_printer_state(self, state: dict) -> None:
        """Every printer state change, as the dict the web app sees."""

    def on_serial_line(self, direction: str, line: str) -> None:
        """Every line on the wire, direction "tx" or "rx"; called from the reader thread, keep it quick."""

    def on_event(self, event: str, payload: dict) -> None:
        """One of EVENTS happened; runs on the host's event thread, so it may take a moment."""

    def save_state(self) -> None:
        self.context.save_state(dict(self.state))


@dataclass
class LoadedPlugin:
    id: str
    path: Path
    version: str
    settings: dict
    module_name: str
    module: ModuleType | None = None
    instance: PluginBase | None = None
    state: str = "stopped"  # installing | running | error | stopped
    error: str | None = None
    details: dict = field(default_factory=dict)


def pip_install(requirements: Path) -> None:
    """Install a plugin's requirements into the interpreter running the daemon."""
    command = [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
               "-r", str(requirements)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=900)
    if result.returncode != 0:
        tail = (result.stderr or result.stdout).strip().splitlines()[-3:]
        raise PluginError("pip install failed: " + " ".join(line.strip() for line in tail))


class PluginHost:
    def __init__(
        self,
        *,
        load_state: Callable[[str], dict] | None = None,
        save_state: Callable[[str, dict], None] | None = None,
        requirements_installed: dict[str, str] | None = None,
        on_requirements_installed: Callable[[str, str], None] | None = None,
        install_requirements: Callable[[Path], None] = pip_install,
        send_gcode: SendGcode | None = None,
        status_changed: Callable[[], None] | None = None,
        printer_control: Callable[[str], None] | None = None,
        printer_ports: Callable[[], list[str]] | None = None,
        last_connection: Callable[[], dict | None] | None = None,
        print_control: Callable[[str], None] | None = None,
        notify: Callable[[str, str, str, str | None], None] | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._plugins: dict[str, LoadedPlugin] = {}
        self._load_state = load_state or (lambda plugin_id: {})
        self._save_state = save_state or (lambda plugin_id, state: None)
        self._requirements_installed = requirements_installed if requirements_installed is not None else {}
        self._on_requirements_installed = on_requirements_installed or (lambda plugin_id, digest: None)
        self._install_requirements = install_requirements
        self._send_gcode = send_gcode or _no_printer
        self._status_changed = status_changed or (lambda: None)
        self._printer_control = printer_control or _no_printer_control
        self._printer_ports = printer_ports or (lambda: [])
        self._last_connection = last_connection or (lambda: None)
        self._print_control = print_control or _no_print_control
        self._notify = notify or (lambda plugin_id, level, message, title: _no_notify(level, message, title))

    @property
    def ids(self) -> list[str]:
        return list(self._plugins)

    def sync(self, specs: list[dict]) -> None:
        """Make the loaded plugins match specs: [{"id", "path", "version", "settings"}].

        Plugins that disappeared are unloaded, new ones loaded, changed settings
        applied, and a changed version or path reloads the module. A plugin in
        the error state is retried, because a sync means the user changed something.
        """
        wanted: dict[str, dict] = {}
        for spec in specs:
            plugin_id = str(spec.get("id", ""))
            if ID_PATTERN.match(plugin_id) and spec.get("path"):
                wanted[plugin_id] = spec
            else:
                log.warning("ignoring malformed plugin spec %r", spec)
        with self._lock:
            for plugin_id in list(self._plugins):
                if plugin_id not in wanted:
                    self._unload(plugin_id)
            for plugin_id, spec in wanted.items():
                path = Path(str(spec["path"]))
                version = str(spec.get("version") or "")
                settings = dict(spec.get("settings") or {})
                current = self._plugins.get(plugin_id)
                if current is None:
                    self._load(plugin_id, path, version, settings)
                elif current.path != path or current.version != version or current.state != "running":
                    self._unload(plugin_id)
                    self._load(plugin_id, path, version, settings)
                elif current.settings != settings:
                    self._apply_settings(current, settings)

    def action(self, plugin_id: str, action: str, value: Any = None) -> dict:
        """Run a control action and return the plugin's status afterwards."""
        with self._lock:
            plugin = self._plugins.get(plugin_id)
            if plugin is None:
                raise PluginError(f"plugin {plugin_id!r} is not loaded")
            if plugin.state != "running" or plugin.instance is None:
                raise PluginError(f"plugin {plugin_id!r} is {plugin.state}: {plugin.error or 'not running'}")
            plugin.instance.handle(str(action), value)
            return self._status_of(plugin)

    def statuses(self) -> dict[str, dict]:
        """State of every loaded plugin, keyed by id; safe to call while a sync installs requirements."""
        return {plugin.id: self._status_of(plugin) for plugin in list(self._plugins.values())}

    def notify_printer_state(self, state: dict) -> None:
        for plugin in self._running():
            try:
                plugin.instance.on_printer_state(state)  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001 - one plugin must not break the state feed
                log.exception("plugin %s failed on printer state", plugin.id)

    def notify_event(self, event: str, payload: dict) -> None:
        for plugin in self._running():
            try:
                plugin.instance.on_event(event, dict(payload))  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001
                log.exception("plugin %s failed on event %s", plugin.id, event)

    def notify_serial_line(self, direction: str, line: str) -> None:
        for plugin in self._running():
            try:
                plugin.instance.on_serial_line(direction, line)  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001
                log.exception("plugin %s failed on serial line", plugin.id)

    def _running(self) -> list[LoadedPlugin]:
        return [plugin for plugin in list(self._plugins.values()) if plugin.state == "running" and plugin.instance]

    def stop_all(self) -> None:
        with self._lock:
            for plugin_id in list(self._plugins):
                self._unload(plugin_id)

    # ---- internals -------------------------------------------------------------------

    def _status_of(self, plugin: LoadedPlugin) -> dict:
        details: dict = {}
        error = plugin.error
        if plugin.state == "running" and plugin.instance is not None:
            try:
                details = dict(plugin.instance.status() or {})
            except Exception as exc:  # noqa: BLE001
                error = f"status failed: {exc}"
        return {"state": plugin.state, "error": error, "version": plugin.version, "status": details}

    def _load(self, plugin_id: str, path: Path, version: str, settings: dict) -> None:
        module_name = MODULE_PREFIX + re.sub(r"[^0-9a-zA-Z_]", "_", plugin_id)
        plugin = LoadedPlugin(plugin_id, path, version, settings, module_name)
        self._plugins[plugin_id] = plugin
        try:
            self._ensure_requirements(plugin)
            plugin.module = self._import(plugin)
            cls = getattr(plugin.module, "Plugin", None)
            if not (isinstance(cls, type) and issubclass(cls, PluginBase)):
                raise PluginError("daemon/plugin.py must define class Plugin(PluginBase)")
            context = PluginContext(
                id=plugin_id,
                path=path,
                settings=settings,
                state=self._safe_load_state(plugin_id),
                save_state=lambda state, plugin_id=plugin_id: self._save_state(plugin_id, state),
                send_gcode=self._send_gcode,
                status_changed=self._status_changed,
                printer_control=self._printer_control,
                printer_ports=self._printer_ports,
                last_connection=self._last_connection,
                print_control=self._print_control,
                notify=lambda level, message, title, plugin_id=plugin_id: self._notify(plugin_id, level, message, title),
            )
            instance = cls(context)
            instance.start()
            plugin.instance, plugin.state, plugin.error = instance, "running", None
            log.info("plugin %s %s loaded from %s", plugin_id, version or "", path)
        except Exception as exc:  # noqa: BLE001 - a bad plugin is reported, not fatal
            plugin.state, plugin.error = "error", f"{type(exc).__name__}: {exc}"
            log.exception("plugin %s failed to load", plugin_id)
            self._drop_module(plugin)

    def _ensure_requirements(self, plugin: LoadedPlugin) -> None:
        requirements = plugin.path / "daemon" / "requirements.txt"
        if not requirements.is_file():
            return
        digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
        if self._requirements_installed.get(plugin.id) == digest:
            return
        plugin.state = "installing"
        log.info("installing requirements for plugin %s", plugin.id)
        self._install_requirements(requirements)
        self._requirements_installed[plugin.id] = digest
        self._on_requirements_installed(plugin.id, digest)

    def _import(self, plugin: LoadedPlugin) -> ModuleType:
        entry = plugin.path / "daemon" / "plugin.py"
        if not entry.is_file():
            raise PluginError(f"{entry} does not exist")
        # A package rooted in daemon/, so plugin.py may import sibling modules relatively.
        spec = importlib.util.spec_from_file_location(
            plugin.module_name, entry, submodule_search_locations=[str(entry.parent)],
        )
        if spec is None or spec.loader is None:
            raise PluginError(f"cannot import {entry}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[plugin.module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            self._drop_module(plugin)
            raise
        return module

    def _apply_settings(self, plugin: LoadedPlugin, settings: dict) -> None:
        plugin.settings = settings
        if plugin.instance is None:
            return
        try:
            plugin.instance.apply_settings(settings)
            plugin.state, plugin.error = "running", None
        except Exception as exc:  # noqa: BLE001
            plugin.state, plugin.error = "error", f"{type(exc).__name__}: {exc}"
            log.exception("plugin %s rejected its settings", plugin.id)

    def _unload(self, plugin_id: str) -> None:
        plugin = self._plugins.pop(plugin_id, None)
        if plugin is None:
            return
        if plugin.instance is not None:
            try:
                plugin.instance.stop()
            except Exception:  # noqa: BLE001
                log.exception("plugin %s failed to stop", plugin_id)
        self._drop_module(plugin)
        log.info("plugin %s unloaded", plugin_id)

    def _drop_module(self, plugin: LoadedPlugin) -> None:
        plugin.module, plugin.instance = None, None
        for name in list(sys.modules):
            if name == plugin.module_name or name.startswith(plugin.module_name + "."):
                sys.modules.pop(name, None)

    def _safe_load_state(self, plugin_id: str) -> dict:
        try:
            state = self._load_state(plugin_id)
        except Exception:  # noqa: BLE001
            log.exception("could not load state for plugin %s", plugin_id)
            return {}
        return dict(state) if isinstance(state, dict) else {}
