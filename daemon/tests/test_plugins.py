"""PluginHost: loading, settings, actions, state and requirements, plus the built-in LED plugin."""

import json
import sys
from pathlib import Path

import pytest

from printpi_daemon.plugins import PluginError, PluginHost

REPO_PLUGINS = Path(__file__).resolve().parents[2] / "plugins"

PLUGIN_SOURCE = '''
from printpi_daemon.plugins import PluginBase, PluginError

class Plugin(PluginBase):
    def start(self):
        self.state["starts"] = self.state.get("starts", 0) + 1
        self.save_state()
        self.stopped = False
        if self.settings.get("explode"):
            raise RuntimeError("boom")

    def stop(self):
        self.stopped = True

    def handle(self, action, value):
        if action == "set_level":
            self.state["level"] = int(value)
            self.save_state()
            return
        raise PluginError(f"unknown action {action!r}")

    def status(self):
        return {"level": self.state.get("level", 0), "pin": self.settings.get("pin"), "starts": self.state["starts"]}

    def on_printer_state(self, state):
        self.last_state = state
'''


def write_plugin(root: Path, plugin_id: str = "demo", source: str = PLUGIN_SOURCE, requirements: str | None = None) -> Path:
    path = root / plugin_id
    (path / "daemon").mkdir(parents=True, exist_ok=True)
    (path / "plugin.json").write_text(json.dumps({"id": plugin_id, "name": plugin_id, "version": "1.0.0"}))
    (path / "daemon" / "plugin.py").write_text(source)
    if requirements is not None:
        (path / "daemon" / "requirements.txt").write_text(requirements)
    return path


def spec(path: Path, version: str = "1.0.0", **settings) -> dict:
    return {"id": path.name, "path": str(path), "version": version, "settings": settings}


@pytest.fixture
def saved() -> dict:
    return {}


@pytest.fixture
def host(saved):
    h = PluginHost(load_state=lambda plugin_id: saved.get(plugin_id, {}), save_state=saved.__setitem__)
    yield h
    h.stop_all()


def test_sync_loads_and_reports_status(tmp_path, host, saved):
    path = write_plugin(tmp_path)
    host.sync([spec(path, pin=18)])
    status = host.statuses()["demo"]
    assert status["state"] == "running"
    assert status["error"] is None
    assert status["version"] == "1.0.0"
    assert status["status"] == {"level": 0, "pin": 18, "starts": 1}
    assert saved["demo"] == {"starts": 1}
    assert "printpi_plugin_demo" in sys.modules


def test_changed_settings_restart_and_removed_plugins_unload(tmp_path, host):
    path = write_plugin(tmp_path)
    host.sync([spec(path, pin=18)])
    instance = host._plugins["demo"].instance
    host.sync([spec(path, pin=10)])
    assert host._plugins["demo"].instance is instance
    assert host.statuses()["demo"]["status"] == {"level": 0, "pin": 10, "starts": 2}
    host.sync([])
    assert instance.stopped
    assert host.statuses() == {}
    assert "printpi_plugin_demo" not in sys.modules


def test_action_updates_persisted_state(tmp_path, host, saved):
    path = write_plugin(tmp_path)
    host.sync([spec(path)])
    status = host.action("demo", "set_level", "7")
    assert status["status"]["level"] == 7
    assert saved["demo"]["level"] == 7
    with pytest.raises(PluginError, match="unknown action"):
        host.action("demo", "explode")
    with pytest.raises(PluginError, match="not loaded"):
        host.action("other", "set_level", 1)


def test_state_survives_a_reload(tmp_path, host, saved):
    path = write_plugin(tmp_path)
    host.sync([spec(path)])
    host.action("demo", "set_level", 3)
    host.sync([spec(path, version="1.1.0")])
    status = host.statuses()["demo"]
    assert status["version"] == "1.1.0"
    assert status["status"]["level"] == 3
    assert status["status"]["starts"] == 2


def test_broken_plugins_report_errors_and_are_retried(tmp_path, host):
    missing = tmp_path / "missing"
    missing.mkdir()
    broken = write_plugin(tmp_path, "broken", "raise ValueError('bad import')")
    no_class = write_plugin(tmp_path, "noclass", "x = 1")
    exploding = write_plugin(tmp_path)
    host.sync([spec(missing), spec(broken), spec(no_class), spec(exploding, explode=True)])
    statuses = host.statuses()
    assert statuses["missing"]["state"] == "error" and "does not exist" in statuses["missing"]["error"]
    assert statuses["broken"]["error"] == "ValueError: bad import"
    assert "class Plugin(PluginBase)" in statuses["noclass"]["error"]
    assert statuses["demo"]["error"] == "RuntimeError: boom"
    assert "printpi_plugin_broken" not in sys.modules
    with pytest.raises(PluginError, match="is error"):
        host.action("demo", "set_level", 1)

    host.sync([spec(exploding, explode=False)])
    assert host.statuses()["demo"]["state"] == "running"


def test_settings_a_plugin_rejects_put_it_in_error(tmp_path, host):
    path = write_plugin(tmp_path)
    host.sync([spec(path)])
    host.sync([spec(path, explode=True)])
    assert host.statuses()["demo"]["state"] == "error"


def test_new_code_is_loaded_when_the_version_changes(tmp_path, host):
    path = write_plugin(tmp_path)
    host.sync([spec(path)])
    write_plugin(tmp_path, source=PLUGIN_SOURCE.replace('"level"', '"volume"'))
    host.sync([spec(path)])
    assert "level" in host.statuses()["demo"]["status"]
    host.sync([spec(path, version="2.0.0")])
    assert "volume" in host.statuses()["demo"]["status"]


def test_requirements_are_installed_once_per_hash(tmp_path):
    installed = []
    recorded = {}
    path = write_plugin(tmp_path, requirements="left-pad==1.0\n")
    host = PluginHost(install_requirements=installed.append, requirements_installed=recorded,
                      on_requirements_installed=lambda plugin_id, digest: recorded.__setitem__(plugin_id, digest))
    host.sync([spec(path)])
    assert installed == [path / "daemon" / "requirements.txt"]
    assert host.statuses()["demo"]["state"] == "running"
    host.sync([spec(path, version="1.0.1")])
    assert len(installed) == 1
    host.stop_all()

    again = PluginHost(install_requirements=installed.append, requirements_installed=dict(recorded))
    again.sync([spec(path)])
    assert len(installed) == 1
    again.stop_all()

    (path / "daemon" / "requirements.txt").write_text("left-pad==2.0\n")
    again.sync([spec(path)])
    assert len(installed) == 2
    again.stop_all()


def test_failed_requirements_put_the_plugin_in_error(tmp_path):
    def fail(requirements):
        raise PluginError("pip install failed: no matching distribution")

    path = write_plugin(tmp_path, requirements="nope\n")
    host = PluginHost(install_requirements=fail)
    host.sync([spec(path)])
    status = host.statuses()["demo"]
    assert status["state"] == "error"
    assert "no matching distribution" in status["error"]


def test_printer_state_reaches_running_plugins(tmp_path, host):
    path = write_plugin(tmp_path)
    host.sync([spec(path)])
    host.notify_printer_state({"connection": "connected"})
    assert host._plugins["demo"].instance.last_state == {"connection": "connected"}


def test_malformed_specs_are_ignored(tmp_path, host):
    path = write_plugin(tmp_path)
    host.sync([{"id": "../etc", "path": "/etc"}, {"id": "demo"}, spec(path)])
    assert host.ids == ["demo"]


# ---- the built-in LED strip plugin ----------------------------------------------------

LED_PATH = REPO_PLUGINS / "led-strip"


def led_spec(**settings) -> dict:
    values = {"strip_type": "ws2812b", "led_count": 4, "gpio_pin": 18, "driver": "simulated"}
    values.update(settings)
    return {"id": "led-strip", "path": str(LED_PATH), "version": "1.1.0", "settings": values}


def test_led_manifest_matches_the_plugin():
    manifest = json.loads((LED_PATH / "plugin.json").read_text())
    assert manifest["id"] == "led-strip"
    assert {field["key"] for field in manifest["settings"]} == {"strip_type", "led_count", "gpio_pin"}
    assert {control["action"] for control in manifest["controls"]} == {"set_power", "set_color", "set_brightness"}
    assert manifest["controls"][0]["actions"] == ["printer_light_on", "printer_light_off"]
    assert manifest["controls"][1]["actions"] == ["printer_light_color"]


def test_led_plugin_renders_colour_brightness_and_power(host, saved):
    host.sync([led_spec()])
    status = host.statuses()["led-strip"]
    assert status["state"] == "running", status["error"]
    assert status["status"]["backend"] == "simulated"
    backend = host._plugins["led-strip"].instance._backend
    assert backend.pixels == [(128, 128, 128, 0)] * 4

    host.action("led-strip", "set_color", "#FF8000")
    host.action("led-strip", "set_brightness", 100)
    assert backend.pixels == [(255, 128, 0, 0)] * 4
    assert saved["led-strip"]["color"] == "#ff8000"

    host.action("led-strip", "set_power", False)
    assert backend.pixels == [(0, 0, 0, 0)] * 4
    assert host.statuses()["led-strip"]["status"]["power"] is False
    assert host.statuses()["led-strip"]["status"]["printer_light"] == {"name": "LED strip", "on": False, "color": "#ff8000"}

    host.action("led-strip", "printer_light_on")
    assert backend.pixels == [(255, 128, 0, 0)] * 4
    assert host.statuses()["led-strip"]["status"]["printer_light"]["on"] is True
    host.action("led-strip", "printer_light_color", "#00FF00")
    assert backend.pixels == [(0, 255, 0, 0)] * 4
    assert host.statuses()["led-strip"]["status"]["printer_light"]["color"] == "#00ff00"
    host.action("led-strip", "printer_light_off")
    assert backend.pixels == [(0, 0, 0, 0)] * 4 and saved["led-strip"]["power"] is False

    with pytest.raises(PluginError, match="colour"):
        host.action("led-strip", "set_color", "red")
    with pytest.raises(PluginError, match="unknown action"):
        host.action("led-strip", "rainbow")


def test_led_plugin_reopens_the_strip_with_new_settings(host):
    host.sync([led_spec()])
    host.sync([led_spec(led_count=2, strip_type="sk6812_rgbw")])
    backend = host._plugins["led-strip"].instance._backend
    assert backend.count == 2 and backend.order == "GRBW"
    host.sync([led_spec(gpio_pin=7)])
    assert "GPIO 7" in host.statuses()["led-strip"]["error"]


def test_led_plugin_turns_the_strip_off_on_stop(host):
    host.sync([led_spec()])
    backend = host._plugins["led-strip"].instance._backend
    host.stop_all()
    assert backend.pixels == [(0, 0, 0, 0)] * 4


def test_bridge_dispatches_plugin_actions():
    from printpi_daemon.bridge import EVENTS_CHANNEL, RedisBridge
    from printpi_daemon.printer import Printer

    bridge = RedisBridge("redis://127.0.0.1:1/0", Printer("fake://?time_scale=0.01"))
    bridge._publish_plugin_status = lambda: None  # no redis in tests
    bridge.plugins._save_state = lambda plugin_id, state: None
    try:
        bridge.plugins.sync([led_spec()])
        bridge._execute({"type": "plugin_action", "id": "led-strip", "action": "set_brightness", "value": 10})
        events = []
        while not bridge._outbox.empty():
            channel, payload = bridge._outbox.get_nowait()
            if channel == EVENTS_CHANNEL:
                events.append(json.loads(payload))
        assert events[-1]["type"] == "plugin_action"
        assert events[-1]["status"]["status"]["brightness"] == 10
        with pytest.raises(PluginError):
            bridge._execute({"type": "plugin_action", "id": "led-strip", "action": "nope"})
    finally:
        bridge.plugins.stop_all()


def test_events_reach_running_plugins_one_failure_at_a_time(tmp_path, host):
    source = PLUGIN_SOURCE + '''
    def on_event(self, event, payload):
        self.events = getattr(self, "events", []) + [(event, payload)]
        if payload.get("explode"):
            raise RuntimeError("boom")
'''
    host.sync([spec(write_plugin(tmp_path, "one", source)), spec(write_plugin(tmp_path, "two", source))])
    host.notify_event("print_started", {"name": "cube.gcode"})
    host.notify_event("print_finished", {"explode": True})
    for plugin_id in ("one", "two"):
        events = host._plugins[plugin_id].instance.events
        assert [event for event, _ in events] == ["print_started", "print_finished"]
        assert events[0][1] == {"name": "cube.gcode"}
    assert host.statuses()["one"]["state"] == "running"


def test_print_control_and_notify_reach_the_host(tmp_path, saved):
    calls: list = []
    host = PluginHost(load_state=lambda plugin_id: {}, save_state=saved.__setitem__,
                      print_control=lambda action: calls.append(("print", action)),
                      notify=lambda plugin_id, level, message, title: calls.append((plugin_id, level, message, title)))
    source = PLUGIN_SOURCE + '''
    def on_event(self, event, payload):
        self.pause_print()
        self.resume_print()
        self.cancel_print()
        self.notify("done", "success", "Demo")
        self.notify("plain")
'''
    try:
        host.sync([spec(write_plugin(tmp_path, "demo", source))])
        host.notify_event("print_finished", {})
    finally:
        host.stop_all()
    assert calls == [("print", "pause"), ("print", "resume"), ("print", "cancel"),
                     ("demo", "success", "done", "Demo"), ("demo", "info", "plain", None)]


def test_plugins_without_a_host_link_cannot_control_the_print(tmp_path, host):
    source = PLUGIN_SOURCE + '''
    def handle(self, action, value):
        self.pause_print()
'''
    host.sync([spec(write_plugin(tmp_path, "demo", source))])
    with pytest.raises(PluginError, match="no print job link"):
        host.action("demo", "anything")
