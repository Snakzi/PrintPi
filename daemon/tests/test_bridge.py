"""Bridge command handling, exercised without a Redis server.

RedisBridge only talks to Redis from its threads; _execute() and the printer
callbacks write to the in-memory outbox, so they can be tested directly.
"""

import json
import os
import time

import pytest

from printpi_daemon.filament import FilamentError, FilamentState
from printpi_daemon.firmware import FirmwareError
from printpi_daemon.bridge import (
    EVENTS_CHANNEL, FILAMENT_DONE_KEY, JOBS_DONE_KEY, STATE_CHANNEL, FAKE_PORT, RedisBridge, list_ports, printer_power_watts,
)
from printpi_daemon.job import JobError
from printpi_daemon.plugins import PluginError
from printpi_daemon.printer import Printer, PrinterError
from printpi_daemon.timelapse import TimelapseRecorder
from tests.test_timelapse import jpeg

FAST = "fake://?time_scale=0.01"


def wait_for(predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def make_bridge() -> RedisBridge:
    printer = Printer(FAST, connect_timeout=1.0, ok_timeout=2.0)
    return RedisBridge("redis://127.0.0.1:1/0", printer)


def drain(bridge: RedisBridge) -> list[tuple[str, dict]]:
    items = []
    while not bridge._outbox.empty():
        channel, payload = bridge._outbox.get_nowait()
        items.append((channel, json.loads(payload)))
    return items


@pytest.fixture
def bridge():
    b = make_bridge()
    yield b
    if b.printer.connected:
        b.printer.disconnect()


def test_connect_command_opens_default_port(bridge):
    bridge._execute({"type": "connect"})
    assert bridge.printer.connected
    events = [payload for channel, payload in drain(bridge) if channel == EVENTS_CHANNEL]
    assert events[-1]["type"] == "connected"
    assert events[-1]["port"] == FAST


def test_connect_command_switches_port_and_baud(bridge):
    original = bridge.printer
    bridge._execute({"type": "connect", "port": FAST + "&latency=0", "baud": 250000})
    assert bridge.printer is not original
    assert bridge.printer.connected
    assert bridge.printer.baudrate == 250000
    assert bridge.printer.serial_log is original.serial_log
    states = [payload for channel, payload in drain(bridge) if channel == STATE_CHANNEL]
    assert states[-1]["connection"] == "connected"
    assert states[-1]["baudrate"] == 250000


def test_reconnect_to_same_port_is_a_noop(bridge):
    bridge._execute({"type": "connect"})
    printer = bridge.printer
    bridge._execute({"type": "connect", "port": FAST, "baud": 115200})
    assert bridge.printer is printer
    assert printer.connected


def test_reconnect_reopens_the_remembered_port(bridge):
    assert bridge._connection_target() == {"port": FAST, "baud": 115200}
    bridge._execute({"type": "reconnect"})  # nothing remembered yet: the daemon's own port
    assert bridge.printer.connected and bridge.printer.port_url == FAST
    bridge._execute({"type": "disconnect"})

    bridge._execute({"type": "connect", "port": FAST + "&latency=0", "baud": 250000})
    assert bridge._last_connection == {"port": FAST + "&latency=0", "baud": 250000}
    bridge._execute({"type": "disconnect"})
    assert not bridge.printer.connected

    bridge._execute({"type": "reconnect"})
    assert bridge.printer.connected and bridge.printer.baudrate == 250000
    assert drain(bridge)[-1][1]["type"] == "connected"


def test_plugins_queue_printer_control_as_commands(bridge):
    bridge._plugin_printer_control("connect")
    bridge._plugin_printer_control("disconnect")
    assert [bridge._commands.get_nowait()["type"] for _ in range(2)] == ["reconnect", "disconnect"]
    with pytest.raises(PluginError):
        bridge._plugin_printer_control("reboot")


def test_gcode_command_reports_response(bridge):
    bridge._execute({"type": "connect"})
    drain(bridge)
    bridge._execute({"type": "gcode", "command": "M115"})
    events = [payload for channel, payload in drain(bridge) if channel == EVENTS_CHANNEL]
    assert events[-1]["type"] == "gcode"
    assert events[-1]["response"][0].startswith("FIRMWARE_NAME:")


def test_gcode_without_connection_raises(bridge):
    # The worker thread turns this into an error event on printpi:events.
    with pytest.raises(PrinterError, match="not connected"):
        bridge._execute({"type": "gcode", "command": "G28"})


@pytest.mark.parametrize("step", ["printer_load", "confirm_loaded"])
def test_native_filament_blocks_manual_plugin_and_firmware_commands_but_not_emergency_stop(bridge, step):
    bridge._execute({"type": "connect"})
    bridge.filament._state = FilamentState("load", backend="firmware", step=step)
    with pytest.raises(PrinterError, match="filament"):
        bridge._execute({"type": "gcode", "command": "G28"})
    with pytest.raises(PrinterError, match="filament"):
        bridge.plugins._send_gcode("M104 S0", 1.0)
    with pytest.raises(FirmwareError, match="filament"):
        bridge._execute({"type": "firmware_flash", "method": "buddy"})
    with pytest.raises(FirmwareError, match="filament"):
        bridge._execute({"type": "firmware_files"})
    assert "G28" not in bridge.printer._port.commands
    assert "M104 S0" not in bridge.printer._port.commands
    bridge._execute({"type": "emergency_stop"})
    assert bridge.printer.state.status == "halted"


def test_disconnect_and_unknown_command(bridge):
    bridge._execute({"type": "connect"})
    bridge._execute({"type": "disconnect"})
    assert not bridge.printer.connected
    bridge._execute({"type": "reboot"})
    events = [payload for channel, payload in drain(bridge) if channel == EVENTS_CHANNEL]
    assert events[-1]["type"] == "error"
    assert "unknown command type" in events[-1]["message"]


def test_print_commands_drive_the_job_and_show_up_in_the_state(bridge, tmp_path):
    path = tmp_path / "cube.gcode"
    path.write_text("G28\n;LAYER_CHANGE\nG1 X10 Y10 E1 F3000\nG1 X0 Y0 E2\n")
    bridge._execute({"type": "connect"})
    drain(bridge)

    bridge._execute({"type": "print_start", "path": str(path), "name": "cube.gcode", "file_id": 5, "estimated_seconds": 90})
    assert wait_for(lambda: bridge.jobs.state.state == "finished")
    items = drain(bridge)
    events = [payload for channel, payload in items if channel == EVENTS_CHANNEL and payload["type"] != "event"]
    assert events[0]["type"] == "print_started" and events[0]["name"] == "cube.gcode"
    states = [payload for channel, payload in items if channel == STATE_CHANNEL]
    assert states[0]["job"]["state"] == "printing" and states[0]["status"] == "printing"
    assert states[-1]["job"]["state"] == "finished"
    assert states[-1]["job"]["file_id"] == 5 and states[-1]["job"]["estimated_seconds"] == 90
    assert states[-1]["job"]["total_layers"] == 1 and states[-1]["status"] == "idle"

    bridge._execute({"type": "print_restart"})
    assert bridge.jobs.state.state == "printing"
    assert wait_for(lambda: bridge.jobs.state.state == "finished")
    assert bridge.printer._port.commands.count("G1 X0 Y0 E2") == 2


def test_print_control_without_a_job_raises(bridge):
    # The worker turns JobError into an error event, like PrinterError.
    with pytest.raises(JobError, match="not connected"):
        bridge._execute({"type": "print_start", "path": "/nowhere.gcode"})
    bridge._execute({"type": "connect"})
    for kind in ("print_pause", "print_resume", "print_cancel", "print_restart"):
        with pytest.raises(JobError):
            bridge._execute({"type": kind})
    states = [payload for channel, payload in drain(bridge) if channel == STATE_CHANNEL]
    assert states[-1]["job"] is None


def test_list_ports_ends_with_the_fake_printer():
    ports = list_ports()
    assert ports[-1]["device"] == FAKE_PORT
    assert all({"device", "description", "hwid"} <= set(port) for port in ports)


def records(bridge: RedisBridge) -> list[dict]:
    return [payload for channel, payload in drain(bridge) if channel == JOBS_DONE_KEY]


def test_an_ended_job_is_filed_with_its_timelapse(bridge, tmp_path):
    frame = jpeg()
    bridge.timelapse = TimelapseRecorder(str(tmp_path), min_interval=0, fetch=lambda url: frame)
    path = tmp_path / "cube.gcode"
    path.write_text("G28\n;LAYER_CHANGE\nG1 X10 Y10 E1 F3000\n;LAYER_CHANGE\nG1 X0 Y0 E2\n")
    bridge._execute({"type": "connect"})
    bridge._execute({"type": "print_start", "path": str(path), "name": "cube.gcode", "camera_url": "http://cam/stream"})
    job_id = bridge.jobs.state.id
    assert bridge.timelapse.recording
    assert wait_for(lambda: bridge.jobs.state.state == "finished")
    assert wait_for(lambda: any(channel == JOBS_DONE_KEY for channel, _ in list(bridge._outbox.queue)))

    items = drain(bridge)
    record = next(payload for channel, payload in items if channel == JOBS_DONE_KEY)
    assert record["id"] == job_id and record["name"] == "cube.gcode" and record["state"] == "finished"
    assert record["progress"] == 1.0 and record["total_layers"] == 2 and record["finished_at"] is not None
    timelapse = record["timelapse"]
    assert timelapse["frames"] == 4 and timelapse["error"] is None  # empty bed, two layers, finished part
    assert os.path.isfile(timelapse["gif"]) and os.path.isfile(timelapse["cover"])
    assert timelapse["gif"].startswith(str(tmp_path / job_id))
    assert not bridge.timelapse.recording
    events = [payload for channel, payload in items if channel == EVENTS_CHANNEL]
    assert events[-1]["type"] == "print_recorded" and events[-1]["id"] == job_id

    # Without any camera the record still comes, just without a timelapse.
    bridge._job_camera_url = None
    bridge._execute({"type": "print_restart"})
    assert not bridge.timelapse.recording
    assert wait_for(lambda: bridge.jobs.state.state == "finished")
    assert wait_for(lambda: any(channel == JOBS_DONE_KEY for channel, _ in list(bridge._outbox.queue)))
    again = records(bridge)[0]
    assert again["id"] != job_id and again["timelapse"] is None


def test_a_cancelled_job_is_filed_too(bridge, tmp_path):
    path = tmp_path / "long.gcode"
    path.write_text("G4 S30\n" + "G1 X1 E1\n" * 50)
    bridge._execute({"type": "connect"})
    bridge._execute({"type": "print_start", "path": str(path)})
    bridge._execute({"type": "print_cancel"})
    assert wait_for(lambda: bridge.jobs.state.state == "cancelled")
    assert wait_for(lambda: any(channel == JOBS_DONE_KEY for channel, _ in list(bridge._outbox.queue)))
    record = records(bridge)[0]
    assert record["state"] == "cancelled" and record["progress"] < 1.0


def test_energy_is_metered_from_the_printer_plug(bridge, tmp_path, monkeypatch):
    path = tmp_path / "slow.gcode"
    path.write_text("G4 S30\n" + "G1 X1 E1\n" * 20)
    bridge._execute({"type": "connect"})
    bridge._meter_energy()  # no job: nothing to meter
    assert bridge._power_sample is None
    bridge._execute({"type": "print_start", "path": str(path)})

    statuses = {"tapo-plug": {"state": "running", "status": {"printer_power": {"id": "p1", "on": True, "power_w": 120.0}}}}
    monkeypatch.setattr(bridge.plugins, "statuses", lambda: statuses)
    bridge._meter_energy()
    assert bridge.jobs.state.energy_wh is None  # the first sample only starts the clock
    job_id, sampled_at, watts = bridge._power_sample
    bridge._power_sample = (job_id, sampled_at - 1800.0, watts)  # pretend half an hour passed
    statuses["tapo-plug"]["status"]["printer_power"]["power_w"] = 80.0
    bridge._meter_energy()
    assert bridge.jobs.state.energy_wh == pytest.approx(50.0, abs=0.1)  # (120 + 80) / 2 W for 0.5 h

    bridge._execute({"type": "print_cancel"})
    assert wait_for(lambda: bridge.jobs.state.state == "cancelled")
    bridge._meter_energy()
    assert bridge._power_sample is None
    assert bridge.jobs.state.energy_wh == pytest.approx(50.0, abs=0.1)


def test_printer_power_watts_needs_a_running_plugin_with_a_reading():
    assert printer_power_watts({}) is None
    assert printer_power_watts({"tapo": {"state": "error", "status": {"printer_power": {"power_w": 5}}}}) is None
    assert printer_power_watts({"tapo": {"state": "running", "status": {"printer_power": {"power_w": None}}}}) is None
    assert printer_power_watts({"tapo": {"state": "running", "status": {"printer_power": {"id": "p", "power_w": 42}}}}) == 42.0


def events_of(bridge: RedisBridge) -> list[tuple[str, dict]]:
    """The events queued for the plugins; the dispatch thread only runs after start()."""
    items = []
    while not bridge._events.empty():
        item = bridge._events.get_nowait()
        if item is not None:
            items.append(item)
    return items


def test_connection_and_job_events_are_emitted(bridge, tmp_path):
    path = tmp_path / "cube.gcode"
    path.write_text("G28\n;LAYER_CHANGE\nG1 X10 Y10 E1 F3000\n;LAYER_CHANGE\nG1 X0 Y0 E2\n")
    bridge._execute({"type": "connect"})
    bridge._execute({"type": "print_start", "path": str(path), "name": "cube.gcode", "file_id": 5})
    assert wait_for(lambda: bridge.jobs.state.state == "finished")
    bridge._execute({"type": "disconnect"})

    events = events_of(bridge)
    names = [name for name, _ in events]
    assert names[0] == "connected" and names[-1] == "disconnected"
    assert names[1] == "print_started" and names.count("layer_changed") == 2 and names[-2] == "print_finished"
    connected = dict(events)["connected"]
    assert connected["port"] == FAST and connected["baud"] == 115200 and "fake" in connected["firmware"]
    started = events[1][1]
    assert started["name"] == "cube.gcode" and started["file_id"] == 5 and started["state"] == "printing"
    finished = events[-2][1]
    assert finished["state"] == "finished" and finished["layer"] == 2 and finished["total_layers"] == 2
    # Every event also goes out on the events channel for anyone listening.
    published = [payload for channel, payload in drain(bridge) if channel == EVENTS_CHANNEL and payload["type"] == "event"]
    assert [payload["event"] for payload in published] == names


def test_a_lost_connection_is_an_error_and_a_disconnect(bridge):
    bridge._execute({"type": "connect"})
    events_of(bridge)
    bridge.printer.disconnect(error="write failed: gone")
    names = dict(events_of(bridge))
    assert names["disconnected"] == {"error": "write failed: gone"}
    assert names["printer_error"] == {"message": "write failed: gone"}


def test_plugins_control_the_print_and_notify(bridge, tmp_path):
    from tests.test_plugins import spec, write_plugin

    source = '''
from printpi_daemon.plugins import PluginBase

class Plugin(PluginBase):
    def on_event(self, event, payload):
        if event == "print_started":
            self.pause_print()
            self.notify(f"{payload['name']} paused for a check", "warning", "Watcher")
'''
    bridge.plugins._save_state = lambda plugin_id, state: None
    bridge.plugins.sync([spec(write_plugin(tmp_path, "watcher", source))])
    path = tmp_path / "cube.gcode"
    path.write_text("G28\n;LAYER_CHANGE\n" + "G1 X10 Y10 E1 F3000\n" * 200)
    bridge._execute({"type": "connect"})
    bridge._execute({"type": "print_start", "path": str(path), "name": "cube.gcode"})
    for item in events_of(bridge):
        bridge.plugins.notify_event(*item)

    # The plugin's pause is queued for the worker like the button in the UI.
    assert bridge._commands.get_nowait() == {"type": "print_pause"}
    bridge._execute({"type": "print_pause"})
    assert wait_for(lambda: bridge.jobs.state.state == "paused")
    notes = [payload for channel, payload in drain(bridge) if channel == "printpi:notifications"]
    assert len(notes) == 1
    assert notes[0]["level"] == "warning" and notes[0]["title"] == "Watcher" and notes[0]["plugin"] == "watcher"
    assert notes[0]["message"] == "cube.gcode paused for a check" and notes[0]["id"] and notes[0]["at"] > 0
    bridge._execute({"type": "print_cancel"})
    assert wait_for(lambda: not bridge.jobs.state.active)
    bridge.plugins.stop_all()


def test_plugin_notifications_fall_back_to_info_and_take_no_title():
    bridge = make_bridge()
    bridge._notify("demo", "loud", "hello", None)
    (channel, payload), = drain(bridge)
    assert channel == "printpi:notifications"
    assert payload["level"] == "info" and payload["title"] is None and payload["message"] == "hello"


def test_print_start_can_switch_the_timelapse_off_or_to_a_gif(bridge, tmp_path):
    frame = jpeg()
    bridge.timelapse = TimelapseRecorder(str(tmp_path), min_interval=0, fetch=lambda url: frame)
    path = tmp_path / "cube.gcode"
    path.write_text("G28\n;LAYER_CHANGE\nG1 X10 Y10 E1 F3000\n;LAYER_CHANGE\nG1 X0 Y0 E2\n")
    bridge._execute({"type": "connect"})

    bridge._execute({"type": "print_start", "path": str(path), "camera_url": "http://cam/stream",
                     "timelapse": {"enabled": False}})
    assert not bridge.timelapse.recording
    assert wait_for(lambda: bridge.jobs.state.state == "finished")
    assert wait_for(lambda: any(channel == JOBS_DONE_KEY for channel, _ in list(bridge._outbox.queue)))
    assert records(bridge)[0]["timelapse"] is None

    bridge._execute({"type": "print_start", "path": str(path), "camera_url": "http://cam/stream",
                     "timelapse": {"enabled": True, "gif": True, "mp4": False}})
    assert bridge.timelapse.recording
    assert wait_for(lambda: bridge.jobs.state.state == "finished")
    assert wait_for(lambda: any(channel == JOBS_DONE_KEY for channel, _ in list(bridge._outbox.queue)))
    timelapse = records(bridge)[0]["timelapse"]
    assert timelapse["gif"] and timelapse["mp4"] is None and timelapse["cover"]


def test_print_start_hands_the_cancel_script_to_the_job(bridge, tmp_path):
    path = tmp_path / "long.gcode"
    path.write_text("G4 S30\n" + "G1 X1 Y1 E0.1 F6000\n" * 100)
    bridge._execute({"type": "connect"})
    bridge._execute({"type": "print_start", "path": str(path), "cancel_gcode": ["M104 S0", "M140 S0"]})
    bridge._execute({"type": "print_cancel"})
    assert wait_for(lambda: bridge.jobs.state.state == "cancelled")
    assert bridge.printer._port.commands[-2:] == ["M104 S0", "M140 S0"]


def test_filament_commands_drive_the_walkthrough_and_record_the_spool(bridge, tmp_path):
    bridge._execute({"type": "connect"})
    drain(bridge)
    spool = {"id": 3, "name": "Galaxy Black", "material": "PLA", "color": "#26262e"}
    bridge._execute({"type": "filament_start", "action": "load", "spool": spool, "material": "PLA", "nozzle": 215,
                     "moves": {"load": [[30, 360], [50, 1500]], "purge": [27, 180]}})
    assert wait_for(lambda: bridge.filament.state.step == "insert")

    with pytest.raises(JobError, match="filament"):
        bridge._execute({"type": "print_start", "path": str(tmp_path / "cube.gcode")})
    with pytest.raises(FilamentError, match="already running"):
        bridge._execute({"type": "filament_start", "action": "unload", "unload_nozzle": 215})

    bridge._execute({"type": "filament_continue"})
    assert wait_for(lambda: bridge.filament.state.step == "check")
    bridge._execute({"type": "filament_answer", "answer": "yes"})
    assert wait_for(lambda: bridge.filament.state.step == "done")

    items = drain(bridge)
    states = [payload for channel, payload in items if channel == STATE_CHANNEL]
    assert states[0]["filament"]["action"] == "load" and states[0]["filament"]["spool"] == spool
    assert states[-1]["filament"]["step"] == "done"
    records = [payload for channel, payload in items if channel == FILAMENT_DONE_KEY]
    assert records == [{"event": "loaded", "spool": spool, "at": records[0]["at"]}]
    events = [payload for channel, payload in items if channel == EVENTS_CHANNEL]
    assert any(e["type"] == "filament_started" for e in events)
    assert any(e["type"] == "event" and e["event"] == "filament_loaded" and e["spool"] == spool for e in events)


def test_filament_start_is_refused_while_a_print_runs(bridge, tmp_path):
    path = tmp_path / "slow.gcode"
    path.write_text("G4 S30\n")
    bridge._execute({"type": "connect"})
    bridge._execute({"type": "print_start", "path": str(path)})
    with pytest.raises(FilamentError, match="print is active"):
        bridge._execute({"type": "filament_start", "action": "unload", "unload_nozzle": 215})
    bridge.jobs.cancel()
    assert wait_for(lambda: not bridge.jobs.state.active, timeout=10)
    with pytest.raises(FilamentError):
        bridge._execute({"type": "filament_cancel"})
