"""The built-in bed level visualizer: mesh report parsing and the probe flow."""

import importlib.util
import json
import sys
import time
from pathlib import Path

import pytest

from printpi_daemon.bridge import PLUGIN_STATUS_KEY, RedisBridge
from printpi_daemon.plugins import PluginError, PluginHost
from printpi_daemon.printer import Printer

PLUGIN_PATH = Path(__file__).resolve().parents[2] / "plugins" / "bed-level-visualizer"
PLUGIN_ID = "bed-level-visualizer"


def _load_mesh_module():
    spec = importlib.util.spec_from_file_location("bed_level_mesh", PLUGIN_PATH / "daemon" / "mesh.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve their annotations through sys.modules
    spec.loader.exec_module(module)
    return module


MeshParser = _load_mesh_module().MeshParser

# Marlin bilinear leveling, G29 T or M420 V; a missing point is "=====".
BILINEAR = """\
Bilinear Leveling Grid:
      0      1      2
 0 +0.012 -0.020 +0.001
 1 +0.005  ===== -0.010
 2 -0.030 +0.040 +0.000
echo:Bed Leveling ON
"""

# Marlin UBL as an Original Prusa MK4S prints it after M420 V: rows count down, the
# current position sits in brackets, the corners carry the extent in mm.
UBL = """\

Bed Topography Report:

    (  0,210)                (250,210)
        0       1       2
 2 |  0.012  -0.020  +0.001
   |
 1 | +0.005    .    -0.010
   |
 0 |[ 0.000] +0.040  +0.030
        0       1       2
    (  0,  0)                (250,  0)

Mesh is valid
Storage slot: -1
echo:Bed Leveling OFF
ok
"""

UBL_CSV = "Bed Topography Report for CSV:\n\n0.012\t-0.020\t0.001\n0.005\tNAN\t-0.010\n0.000\t0.040\t0.030\nok\n"

# Original Prusa i3 MK3, G81: unlabelled rows from the back of the bed.
PRUSA_G81 = """\
Num X,Y: 3,3
Z search height: 5.00
Measured points:
  0.04667  0.04333  0.04000
  0.02000  0.01000  0.00000
  -0.01000  -0.02000  -0.03000
ok
"""

SUBDIVIDED = """\
Bilinear Leveling Grid:
      0      1
 0 +0.010 +0.020
 1 +0.030 +0.040
Subdivided with CATMULL ROM Leveling Grid:
      0      1      2      3
 0 +0.010 +0.013 +0.017 +0.020
 1 +0.017 +0.020 +0.023 +0.027
 2 +0.023 +0.027 +0.030 +0.033
 3 +0.030 +0.033 +0.037 +0.040
ok
"""


def parse(text: str) -> list:
    parser = MeshParser()
    return [mesh for line in text.splitlines() if (mesh := parser.feed(line)) is not None]


def test_parses_marlin_bilinear_grid_with_missing_points():
    (mesh,) = parse(BILINEAR)
    assert mesh.format == "bilinear"
    assert mesh.z == [[0.012, -0.02, 0.001], [0.005, None, -0.01], [-0.03, 0.04, 0.0]]
    assert mesh.x is None and mesh.y is None
    assert mesh.to_dict()["rows"] == 3 and mesh.to_dict()["cols"] == 3


def test_parses_ubl_report_bottom_up_with_extent():
    (mesh,) = parse(UBL)
    assert mesh.format == "ubl"
    assert mesh.z == [[0.0, 0.04, 0.03], [0.005, None, -0.01], [0.012, -0.02, 0.001]]
    assert mesh.x == [0.0, 125.0, 250.0]
    assert mesh.y == [0.0, 105.0, 210.0]


def test_parses_ubl_csv_and_prusa_g81_which_count_down_without_labels():
    (csv,) = parse(UBL_CSV)
    assert csv.z == [[0.0, 0.04, 0.03], [0.005, None, -0.01], [0.012, -0.02, 0.001]]
    (g81,) = parse(PRUSA_G81)
    assert g81.format == "mbl"
    assert g81.z == [[-0.01, -0.02, -0.03], [0.02, 0.01, 0.0], [0.04667, 0.04333, 0.04]]


def test_keeps_the_measured_grid_and_skips_the_subdivided_one():
    (mesh,) = parse(SUBDIVIDED)
    assert mesh.z == [[0.01, 0.02], [0.03, 0.04]]


def test_chatter_inside_a_report_does_not_split_it():
    lines = UBL.splitlines()
    index = lines.index("   |")
    lines[index:index] = [" T:170.00/170.00 B:60.00/60.00 X:40.0/0.0 A:35.0/0.0 @:0 B@:0 HBR@:0", "echo:busy: processing", "wait"]
    (mesh,) = parse("\n".join(lines))
    assert mesh.rows == 3 and mesh.z[2] == [0.012, -0.02, 0.001]


def test_ignores_chatter_and_incomplete_reports():
    assert parse("ok T:25.00 /0.00 B:24.00 /0.00 @:0 B@:0\nX:0.00 Y:0.00 Z:0.00 E:0.00\necho:busy: processing\n") == []
    assert parse("Bilinear Leveling Grid:\nok\n") == []
    assert parse("Bilinear Leveling Grid:\n 0 +0.010 +0.020\n 1 +0.030\nok\n") == []
    assert parse("Measured points:\n  0.010  0.020\nok\n") == []


# ---- the plugin ----------------------------------------------------------------------


def manifest() -> dict:
    return json.loads((PLUGIN_PATH / "plugin.json").read_text())


def spec(**settings) -> dict:
    values = {"gcode": "G28\nG29\nM420 V", "tolerance": 0.1}
    values.update(settings)
    return {"id": PLUGIN_ID, "path": str(PLUGIN_PATH), "version": "1.0.0", "settings": values}


def wait_for(condition, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "timed out"
        time.sleep(0.01)


def mesh_status(host: PluginHost) -> dict:
    return host.statuses()[PLUGIN_ID]["status"]["mesh"]


def test_manifest_matches_the_plugin():
    data = manifest()
    assert data["id"] == PLUGIN_ID
    assert [field["key"] for field in data["settings"]] == ["gcode", "tolerance", "x_min", "x_max", "y_min", "y_max"]
    assert data["settings"][0]["type"] == "text"
    # Prusa's own recipe: heat first, so a filament rest on the cold nozzle cannot trigger the load cell early.
    assert data["settings"][0]["default"].splitlines()[:6] == ["M140 S60", "M104 S170", "M190 S60", "M109 R170", "G28", "G29"]
    assert data["controls"] == [{"key": "mesh", "label": "Bed mesh", "type": "mesh", "action": "probe"}]


def test_probe_sends_the_commands_and_keeps_the_reported_mesh():
    saved = {}
    sent = []
    host = PluginHost(save_state=saved.__setitem__)

    def send(command, timeout):
        sent.append((command, timeout))
        if command == "M420 V":
            for line in BILINEAR.splitlines():
                host.notify_serial_line("rx", line)
        return []

    host._send_gcode = send
    host.sync([spec()])
    try:
        assert mesh_status(host) == {
            "probing": False, "error": None, "tolerance": 0.1, "measured_at": None, "source": None,
            "step": None, "step_index": 0, "step_count": 0, "points": 0, "points_total": None,
        }
        host.action(PLUGIN_ID, "probe")
        wait_for(lambda: not mesh_status(host)["probing"])
        assert [command for command, _ in sent] == ["G28", "G29", "M420 V"]
        assert all(timeout > 60 for _, timeout in sent)
        status = mesh_status(host)
        assert status["error"] is None
        assert status["source"] == "probe"
        assert status["rows"] == 3 and status["cols"] == 3
        assert status["z"][1] == [0.005, None, -0.01]
        assert saved[PLUGIN_ID]["mesh"]["format"] == "bilinear"
        with pytest.raises(PluginError, match="unknown action"):
            host.action(PLUGIN_ID, "clear")
    finally:
        host.stop_all()


def test_probe_reports_a_printer_that_stays_silent_and_a_missing_connection():
    sent = []
    host = PluginHost(send_gcode=lambda command, timeout: sent.append(command))
    host.sync([spec(gcode="  G29 ; probe the whole bed\n\n; report follows\nM420 V  \n")])
    try:
        host.action(PLUGIN_ID, "probe")
        wait_for(lambda: not mesh_status(host)["probing"])
        assert sent == ["G29", "M420 V"]
        assert mesh_status(host)["error"] == "The printer did not report a mesh"
    finally:
        host.stop_all()

    host = PluginHost()
    host.sync([spec()])
    try:
        host.action(PLUGIN_ID, "probe")
        wait_for(lambda: not mesh_status(host)["probing"])
        assert "no printer" in mesh_status(host)["error"]
    finally:
        host.stop_all()

    host = PluginHost()
    host.sync([spec(gcode="; nothing but comments\n")])
    try:
        host.action(PLUGIN_ID, "probe")
        wait_for(lambda: not mesh_status(host)["probing"])
        assert mesh_status(host)["error"] == "No G-code configured"
    finally:
        host.stop_all()


def test_probe_reports_its_step_and_counts_points_and_learns_the_total():
    saved = {}
    changes = []
    seen = []
    host = PluginHost(load_state=lambda plugin_id: saved.get(plugin_id, {}), save_state=saved.__setitem__,
                      status_changed=lambda: changes.append(mesh_status(host)))

    def send_buddy(command, timeout):
        if command == "G29":
            for _ in range(3):
                host.notify_serial_line("rx", "echo:Starting probe at 1")
                host.notify_serial_line("rx", "echo:Probe classified as clean and OK")
            host.notify_serial_line("rx", "echo:Probe classified as NOK (feature-out-of-range)")
            seen.append(mesh_status(host))
        elif command == "M420 V":
            for line in BILINEAR.splitlines():
                host.notify_serial_line("rx", line)
        return []

    def send_ubl(command, timeout):
        if command == "G29":
            host.notify_serial_line("rx", "Probing mesh point 4/9.")
            seen.append(mesh_status(host))
        return []

    host._send_gcode = send_buddy
    host.sync([spec()])
    try:
        host.action(PLUGIN_ID, "probe")
        wait_for(lambda: not mesh_status(host)["probing"])
        during = seen[0]
        assert (during["step"], during["step_index"], during["step_count"]) == ("G29", 2, 3)
        assert during["points"] == 3 and during["points_total"] is None
        assert [change["points"] for change in changes if change["step"] == "G29"][:4] == [0, 1, 2, 3]
        after = mesh_status(host)
        assert after["step"] is None and after["points"] == 0 and after["points_total"] == 3
        assert saved[PLUGIN_ID]["probe_points"] == 3

        host._plugins[PLUGIN_ID].instance.context.send_gcode = send_ubl
        host.action(PLUGIN_ID, "probe")
        wait_for(lambda: not mesh_status(host)["probing"])
        assert (seen[1]["points"], seen[1]["points_total"]) == (4, 9)
    finally:
        host.stop_all()


FLAT = "Bilinear Leveling Grid:\n      0      1\n 0 +0.000 +0.000\n 1 +0.000 +0.000\nok\n"


def test_probe_is_refused_while_a_print_runs():
    sent = []
    host = PluginHost(send_gcode=lambda command, timeout: sent.append(command))
    host.sync([spec(gcode="G29")])
    try:
        host.notify_printer_state({"job": {"state": "printing"}})
        with pytest.raises(PluginError, match="print is running"):
            host.action(PLUGIN_ID, "probe")
        host.notify_printer_state({"job": {"state": "finished"}})
        host.action(PLUGIN_ID, "probe")
        wait_for(lambda: not mesh_status(host)["probing"])
        assert sent == ["G29"]
    finally:
        host.stop_all()


def test_flat_reports_are_ignored():
    host = PluginHost()

    def send(command, timeout):
        for line in FLAT.splitlines():
            host.notify_serial_line("rx", line)
        return []

    host._send_gcode = send
    host.sync([spec(gcode="M420 V")])
    try:
        for line in FLAT.splitlines():
            host.notify_serial_line("rx", line)
        assert "z" not in mesh_status(host)
        host.action(PLUGIN_ID, "probe")
        wait_for(lambda: not mesh_status(host)["probing"])
        assert mesh_status(host)["error"] == "The printer reported a mesh without values"
    finally:
        host.stop_all()


def test_changing_the_sequence_forgets_the_learned_total():
    saved = {}
    host = PluginHost(load_state=lambda plugin_id: saved.get(plugin_id, {}), save_state=saved.__setitem__)

    def send(command, timeout):
        if command == "G29":
            host.notify_serial_line("rx", "echo:Probe classified as clean and OK")
        return []

    host._send_gcode = send
    host.sync([spec(gcode="G29")])
    try:
        host.action(PLUGIN_ID, "probe")
        wait_for(lambda: not mesh_status(host)["probing"])
        assert mesh_status(host)["points_total"] == 1
        host.sync([spec(gcode="G29", tolerance=0.2)])
        assert mesh_status(host)["points_total"] == 1
        host.sync([spec(gcode="G28\nG29")])
        assert mesh_status(host)["points_total"] is None
        assert "probe_points" not in saved[PLUGIN_ID]
    finally:
        host.stop_all()


def test_area_settings_place_a_report_without_extent():
    host = PluginHost()
    host.sync([spec(x_min=10, x_max=240, y_min=10, y_max=200)])
    try:
        for line in BILINEAR.splitlines():
            host.notify_serial_line("rx", line)
        status = mesh_status(host)
        assert status["x"] == [10.0, 125.0, 240.0] and status["y"] == [10.0, 105.0, 200.0]
        host.sync([spec()])
        assert mesh_status(host)["x"] is None
    finally:
        host.stop_all()


def test_a_mesh_on_the_serial_stream_is_picked_up_and_survives_a_restart():
    saved = {}
    host = PluginHost(load_state=lambda plugin_id: saved.get(plugin_id, {}), save_state=saved.__setitem__)
    host.sync([spec()])
    try:
        for line in UBL.splitlines():
            host.notify_serial_line("rx", line)
        status = mesh_status(host)
        assert status["source"] == "serial"
        assert status["x"] == [0.0, 125.0, 250.0]
        host.sync([spec(tolerance=0.05)])
        status = mesh_status(host)
        assert status["tolerance"] == 0.05 and status["rows"] == 3
    finally:
        host.stop_all()


def test_bad_settings_put_the_plugin_in_error():
    host = PluginHost()
    host.sync([spec(tolerance=0)])
    assert "tolerance" in host.statuses()[PLUGIN_ID]["error"]
    host.stop_all()


def test_probe_through_the_bridge_and_the_fake_printer():
    bridge = RedisBridge("redis://127.0.0.1:1/0", Printer("fake://?time_scale=0.01", connect_timeout=1.0, ok_timeout=2.0))
    bridge.plugins._save_state = lambda plugin_id, state: None
    default_gcode = manifest()["settings"][0]["default"]
    try:
        bridge._execute({"type": "connect"})
        bridge.plugins.sync([spec(gcode=default_gcode)])
        bridge._execute({"type": "plugin_action", "id": PLUGIN_ID, "action": "probe"})
        wait_for(lambda: not mesh_status(bridge.plugins)["probing"], timeout=15.0)
        status = mesh_status(bridge.plugins)
        assert status["error"] is None
        assert status["rows"] == 5 and status["cols"] == 5
        assert status["z"][2][2] == pytest.approx(-0.06)
        assert status["points_total"] == 25  # the fake reports every probed point
        published = []
        while not bridge._outbox.empty():
            channel, payload = bridge._outbox.get_nowait()
            if channel == PLUGIN_STATUS_KEY:
                published.append(json.loads(payload)[PLUGIN_ID]["status"]["mesh"])
        steps = [entry["step"] for entry in published]
        distinct = [step for index, step in enumerate(steps) if index == 0 or step != steps[index - 1]]
        assert distinct == default_gcode.splitlines() + [None]
        assert max(entry["points"] for entry in published) == 25
        fake = bridge.printer._port
        assert [command for command in fake.commands if command != "M105"][-9:] == default_gcode.splitlines()
        assert fake.hotend.target == 0 and fake.bed.target == 0
    finally:
        bridge.plugins.stop_all()
        bridge.printer.disconnect()
