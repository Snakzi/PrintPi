"""The built-in Tapo plug plugin against its fake network."""

import json
import time
from pathlib import Path

import pytest

from printpi_daemon.plugins import PluginError, PluginHost

PLUGIN_PATH = Path(__file__).resolve().parents[2] / "plugins" / "tapo-plug"
PLUGIN_ID = "tapo-plug"


def spec(**settings) -> dict:
    values = {"username": "me@example.com", "password": "secret", "driver": "fake"}
    values.update(settings)
    return {"id": PLUGIN_ID, "path": str(PLUGIN_PATH), "version": "1.2.0", "settings": values}


def wait_for(condition, timeout: float = 3.0):
    """Poll until condition returns something true and return it; the worker thread is asynchronous."""
    deadline = time.monotonic() + timeout
    while True:
        result = condition()
        if result:
            return result
        if time.monotonic() > deadline:
            raise AssertionError("condition not met in time")
        time.sleep(0.02)


def plugs(host: PluginHost) -> dict:
    return host.statuses()[PLUGIN_ID]["status"]["plugs"]


def report_when(host: PluginHost, predicate):
    def check():
        report = plugs(host)
        return report if predicate(report) else None

    return check


def device_when(host: PluginHost, index: int, predicate):
    def check():
        devices = plugs(host)["devices"]
        return devices[index] if len(devices) > index and predicate(devices[index]) else None

    return check


@pytest.fixture
def saved() -> dict:
    return {}


@pytest.fixture
def host(saved):
    h = PluginHost(load_state=lambda plugin_id: saved.get(plugin_id, {}), save_state=saved.__setitem__)
    yield h
    h.stop_all()


def test_manifest_matches_the_plugin():
    manifest = json.loads((PLUGIN_PATH / "plugin.json").read_text())
    assert manifest["id"] == PLUGIN_ID
    assert {field["key"] for field in manifest["settings"]} == {"username", "password", "auto_connect", "auto_off", "auto_off_minutes"}
    (control,) = manifest["controls"]
    assert control["type"] == "devices" and control["action"] == "scan"
    assert set(control["actions"]) == {
        "add", "rename", "remove", "turn_on", "turn_off", "set_printer", "printer_power_on", "printer_power_off",
    }


def test_start_scans_and_found_plugs_can_be_added(host, saved):
    host.sync([spec()])
    assert host.statuses()[PLUGIN_ID]["state"] == "running", host.statuses()[PLUGIN_ID]["error"]
    report = wait_for(report_when(host, lambda r: r["scanned_at"] and not r["scanning"]))
    assert report["error"] is None and report["signed_in"] is True
    assert [entry["id"] for entry in report["found"]] == ["fake-p115", "fake-hs100"]
    assert report["found"][0] == {"id": "fake-p115", "name": "Printer", "model": "P115", "host": "192.168.1.50", "needs_auth": False}
    assert report["devices"] == []

    host.action(PLUGIN_ID, "add", "fake-p115")
    device = wait_for(device_when(host, 0, lambda d: d["online"]))
    assert device["name"] == "Printer" and device["model"] == "P115" and device["host"] == "192.168.1.50"
    assert device["on"] is False and device["power_w"] == 0.2 and device["energy_today_kwh"] == 0.37
    assert [entry["id"] for entry in plugs(host)["found"]] == ["fake-hs100"]
    assert saved[PLUGIN_ID]["devices"][0]["connection"]["device_family"] == "SMART.TAPOPLUG"
    json.dumps(host.statuses())

    with pytest.raises(PluginError, match="already added"):
        host.action(PLUGIN_ID, "add", "fake-p115")
    with pytest.raises(PluginError, match="was found"):
        host.action(PLUGIN_ID, "add", "nope")


@pytest.fixture
def printer_link():
    """What the bridge would offer: the connect calls, the ports it sees and the last connect target."""
    return {"calls": [], "ports": [], "last": {"port": "/dev/ttyACM0", "baud": 115200}}


@pytest.fixture
def linked_host(saved, printer_link):
    h = PluginHost(
        load_state=lambda plugin_id: saved.get(plugin_id, {}), save_state=saved.__setitem__,
        printer_control=printer_link["calls"].append, printer_ports=lambda: list(printer_link["ports"]),
        last_connection=lambda: printer_link["last"],
    )
    yield h
    h.stop_all()


def test_the_printer_plug_powers_and_connects_the_printer(linked_host, saved, printer_link):
    host = linked_host
    host.sync([spec()])
    wait_for(report_when(host, lambda r: r["found"]))
    host.action(PLUGIN_ID, "add", "fake-p115")
    wait_for(device_when(host, 0, lambda d: d["online"]))
    assert host.statuses()[PLUGIN_ID]["status"]["printer_power"] is None
    with pytest.raises(PluginError, match="marked as powering"):
        host.action(PLUGIN_ID, "printer_power_on")

    host.action(PLUGIN_ID, "set_printer", "fake-p115")
    status = host.statuses()[PLUGIN_ID]["status"]
    assert status["printer_power"] == {"id": "fake-p115", "name": "Printer", "on": False, "online": True, "power_w": 0.2}
    assert status["plugs"]["devices"][0]["printer"] is True
    assert saved[PLUGIN_ID]["printer_device"] == "fake-p115"

    # On: the plug switches, then the printer is connected as soon as its port is there.
    host.action(PLUGIN_ID, "printer_power_on")
    wait_for(device_when(host, 0, lambda d: d["on"]))
    time.sleep(0.3)
    assert printer_link["calls"] == []
    printer_link["ports"].append("/dev/ttyACM0")
    wait_for(lambda: printer_link["calls"] == ["connect"])
    host.notify_printer_state({"connection": "connected"})
    instance = host._plugins[PLUGIN_ID].instance
    wait_for(lambda: not instance._auto_connect_thread.is_alive())

    # Off: the port is closed first, the plug goes off once the printer reports offline.
    host.action(PLUGIN_ID, "printer_power_off")
    wait_for(lambda: printer_link["calls"] == ["connect", "disconnect"])
    time.sleep(0.2)
    assert plugs(host)["devices"][0]["on"] is True
    host.notify_printer_state({"connection": "offline"})
    wait_for(device_when(host, 0, lambda d: d["on"] is False))

    host.action(PLUGIN_ID, "set_printer", "")
    assert host.statuses()[PLUGIN_ID]["status"]["printer_power"] is None
    with pytest.raises(PluginError, match="is added"):
        host.action(PLUGIN_ID, "set_printer", "nope")


def test_a_printer_plug_switched_on_elsewhere_connects_too(linked_host, printer_link):
    host = linked_host
    printer_link["ports"].append("/dev/ttyACM0")
    host.sync([spec()])
    wait_for(report_when(host, lambda r: r["found"]))
    host.action(PLUGIN_ID, "add", "fake-p115")
    wait_for(device_when(host, 0, lambda d: d["online"]))
    host.action(PLUGIN_ID, "set_printer", "fake-p115")

    instance = host._plugins[PLUGIN_ID].instance
    instance._network.plugs["fake-p115"]["on"] = True
    instance._jobs.put(instance._refresh)  # what the worker does every REFRESH_INTERVAL
    wait_for(lambda: printer_link["calls"] == ["connect"])
    host.notify_printer_state({"connection": "connected"})


def test_auto_connect_retries_after_a_failed_attempt(linked_host, printer_link):
    host = linked_host
    printer_link["ports"].append("/dev/ttyACM0")
    host.sync([spec()])
    wait_for(report_when(host, lambda r: r["found"]))
    host.action(PLUGIN_ID, "add", "fake-p115")
    wait_for(device_when(host, 0, lambda d: d["online"]))
    host.action(PLUGIN_ID, "set_printer", "fake-p115")
    host._plugins[PLUGIN_ID].module.CONNECT_RETRY = 0.05

    host.action(PLUGIN_ID, "printer_power_on")
    wait_for(lambda: printer_link["calls"] == ["connect"])
    host.notify_printer_state({"connection": "connecting"})
    host.notify_printer_state({"connection": "error", "last_error": "could not open /dev/ttyACM0"})
    wait_for(lambda: printer_link["calls"] == ["connect", "connect"])
    host.notify_printer_state({"connection": "connecting"})
    host.notify_printer_state({"connection": "connected"})
    instance = host._plugins[PLUGIN_ID].instance
    wait_for(lambda: not instance._auto_connect_thread.is_alive())
    assert printer_link["calls"] == ["connect", "connect"]


def test_auto_connect_can_be_turned_off(linked_host, printer_link):
    host = linked_host
    printer_link["ports"].append("/dev/ttyACM0")
    host.sync([spec(auto_connect=False)])
    wait_for(report_when(host, lambda r: r["found"]))
    host.action(PLUGIN_ID, "add", "fake-p115")
    wait_for(device_when(host, 0, lambda d: d["online"]))
    host.action(PLUGIN_ID, "set_printer", "fake-p115")
    host.action(PLUGIN_ID, "printer_power_on")
    wait_for(device_when(host, 0, lambda d: d["on"]))
    time.sleep(0.3)
    assert printer_link["calls"] == []


def test_plugs_can_be_named_when_added_and_renamed_later(host, saved):
    host.sync([spec()])
    wait_for(report_when(host, lambda r: r["found"]))
    host.action(PLUGIN_ID, "add", {"id": "fake-p115", "name": "  Printer power  "})
    host.action(PLUGIN_ID, "add", {"id": "fake-hs100", "name": ""})
    device = wait_for(device_when(host, 0, lambda d: d["online"]))
    assert device["name"] == "Printer power" and device["plug_name"] == "Printer"
    assert plugs(host)["devices"][1]["name"] == "Lights" and "label" not in saved[PLUGIN_ID]["devices"][1]
    assert saved[PLUGIN_ID]["devices"][0]["label"] == "Printer power"

    host.action(PLUGIN_ID, "rename", {"id": "fake-hs100", "name": "Enclosure lights"})
    assert plugs(host)["devices"][1]["name"] == "Enclosure lights"
    assert plugs(host)["devices"][1]["plug_name"] == "Lights"

    # The plug's own app renames it: the label stays, plug_name follows.
    network = host._plugins[PLUGIN_ID].instance._network
    network.plugs["fake-p115"]["name"] = "Prusa"
    host.action(PLUGIN_ID, "scan")
    device = wait_for(device_when(host, 0, lambda d: d["plug_name"] == "Prusa"))
    assert device["name"] == "Printer power"

    host.action(PLUGIN_ID, "rename", {"id": "fake-p115", "name": ""})
    assert plugs(host)["devices"][0]["name"] == "Prusa" and "label" not in saved[PLUGIN_ID]["devices"][0]
    with pytest.raises(PluginError, match="is added"):
        host.action(PLUGIN_ID, "rename", {"id": "nope", "name": "x"})


def test_plugs_switch_and_report_power(host):
    host.sync([spec()])
    wait_for(report_when(host, lambda r: r["found"]))
    host.action(PLUGIN_ID, "add", "fake-p115")
    host.action(PLUGIN_ID, "add", "fake-hs100")
    wait_for(report_when(host, lambda r: len(r["devices"]) == 2 and all(d["online"] for d in r["devices"])))

    host.action(PLUGIN_ID, "turn_on", "fake-p115")
    device = wait_for(device_when(host, 0, lambda d: d["on"]))
    assert device["power_w"] == 118.4
    host.action(PLUGIN_ID, "turn_off", "fake-hs100")
    device = wait_for(device_when(host, 1, lambda d: not d["on"]))
    assert device["power_w"] is None and device["online"] is True

    with pytest.raises(PluginError, match="is added"):
        host.action(PLUGIN_ID, "turn_on", "fake-nope")
    with pytest.raises(PluginError, match="unknown action"):
        host.action(PLUGIN_ID, "blink", "fake-p115")


def test_unreachable_plugs_go_offline_and_come_back(host):
    host.sync([spec()])
    wait_for(report_when(host, lambda r: r["found"]))
    host.action(PLUGIN_ID, "add", "fake-hs100")
    wait_for(device_when(host, 0, lambda d: d["online"]))
    network = host._plugins[PLUGIN_ID].instance._network
    network.unreachable.add("fake-hs100")
    host.action(PLUGIN_ID, "turn_on", "fake-hs100")
    device = wait_for(device_when(host, 0, lambda d: d["online"] is False))
    assert device["error"] == "Unreachable"
    network.unreachable.clear()
    host.action(PLUGIN_ID, "turn_on", "fake-hs100")
    device = wait_for(device_when(host, 0, lambda d: d["online"]))
    assert device["error"] is None and device["on"] is True


def test_removed_plugs_are_forgotten(host, saved):
    host.sync([spec()])
    wait_for(report_when(host, lambda r: r["found"]))
    host.action(PLUGIN_ID, "add", "fake-hs100")
    host.action(PLUGIN_ID, "remove", "fake-hs100")
    report = plugs(host)
    assert report["devices"] == [] and saved[PLUGIN_ID]["devices"] == []
    assert "fake-hs100" in [entry["id"] for entry in report["found"]]
    with pytest.raises(PluginError, match="is added"):
        host.action(PLUGIN_ID, "remove", "fake-hs100")


def test_tapo_plugs_wait_for_the_account(host):
    host.sync([spec(username="", password="")])
    report = wait_for(report_when(host, lambda r: r["scanned_at"]))
    assert report["signed_in"] is False
    assert report["error"] == "Sign in with the TP-Link account to use the Tapo plugs"
    tapo, kasa = report["found"]
    assert tapo["needs_auth"] is True and tapo["name"] is None and tapo["model"] == "P115"
    assert kasa["needs_auth"] is False and kasa["name"] == "Lights"
    with pytest.raises(PluginError, match="sign in"):
        host.action(PLUGIN_ID, "add", "fake-p115")
    host.action(PLUGIN_ID, "add", "fake-hs100")
    wait_for(device_when(host, 0, lambda d: d["online"]))


def test_added_plugs_survive_a_restart_and_follow_a_new_address(host, saved):
    host.sync([spec()])
    wait_for(report_when(host, lambda r: r["found"]))
    host.action(PLUGIN_ID, "add", "fake-p115")
    wait_for(device_when(host, 0, lambda d: d["online"]))
    host.stop_all()

    host.sync([spec()])
    assert plugs(host)["devices"][0]["id"] == "fake-p115"
    wait_for(report_when(host, lambda r: r["scanned_at"] and not r["scanning"] and r["devices"][0]["online"]))
    network = host._plugins[PLUGIN_ID].instance._network
    network.plugs["fake-p115"]["host"] = "192.168.1.77"
    network.plugs["fake-p115"]["name"] = "Prusa"
    host.action(PLUGIN_ID, "scan")
    device = wait_for(device_when(host, 0, lambda d: d["host"] == "192.168.1.77" and d["online"]))
    assert device["name"] == "Prusa"
    assert saved[PLUGIN_ID]["devices"][0]["host"] == "192.168.1.77"


@pytest.fixture
def notifying_host(saved, printer_link):
    notes: list = []
    h = PluginHost(
        load_state=lambda plugin_id: saved.get(plugin_id, {}), save_state=saved.__setitem__,
        printer_control=printer_link["calls"].append, printer_ports=lambda: list(printer_link["ports"]),
        last_connection=lambda: printer_link["last"],
        notify=lambda plugin_id, level, message, title: notes.append((level, title, message)),
    )
    h.notes = notes
    yield h
    h.stop_all()


def printer_plug_on(host: PluginHost) -> None:
    host.sync([spec(auto_connect=False, auto_off=True, auto_off_minutes=1)])
    wait_for(report_when(host, lambda r: r["found"]))
    host.action(PLUGIN_ID, "add", "fake-p115")
    host.action(PLUGIN_ID, "set_printer", "fake-p115")
    host.action(PLUGIN_ID, "turn_on", "fake-p115")
    wait_for(device_when(host, 0, lambda d: d["on"]))


def test_the_printer_plug_goes_off_after_a_finished_print(notifying_host, printer_link, monkeypatch):
    host = notifying_host
    printer_plug_on(host)
    monkeypatch.setattr(host._plugins[PLUGIN_ID].module, "MINUTE", 0.05)
    host.notify_printer_state({"connection": "connected"})
    host.notify_event("print_finished", {"name": "cube.gcode"})
    # The port is closed first, like a click on the power button, then the plug goes off.
    wait_for(lambda: printer_link["calls"] == ["disconnect"])
    host.notify_printer_state({"connection": "offline"})
    wait_for(device_when(host, 0, lambda d: d["on"] is False))
    assert host.notes == [("info", "Tapo Plug", "Printer switched off, the print is done")]


def test_a_new_print_stops_the_auto_off(notifying_host, monkeypatch):
    host = notifying_host
    printer_plug_on(host)
    monkeypatch.setattr(host._plugins[PLUGIN_ID].module, "MINUTE", 0.2)
    host.notify_event("print_finished", {"name": "cube.gcode"})
    host.notify_event("print_started", {"name": "next.gcode"})
    time.sleep(0.4)
    assert plugs(host)["devices"][0]["on"] is True
    assert host.notes == []


def test_auto_off_stays_quiet_when_switched_off_or_without_a_printer_plug(notifying_host, monkeypatch):
    host = notifying_host
    host.sync([spec(auto_connect=False, auto_off=False, auto_off_minutes=0)])
    wait_for(report_when(host, lambda r: r["found"]))
    host.action(PLUGIN_ID, "add", "fake-p115")
    host.action(PLUGIN_ID, "turn_on", "fake-p115")
    wait_for(device_when(host, 0, lambda d: d["on"]))
    host.notify_event("print_finished", {})
    time.sleep(0.2)
    assert plugs(host)["devices"][0]["on"] is True
