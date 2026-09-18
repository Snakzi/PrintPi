"""Firmware updates against the fake printer and a fake avrdude."""

import io
import json
import time

import pytest

from printpi_daemon import fake_printer
from printpi_daemon.bridge import EVENTS_CHANNEL, FIRMWARE_FILES_KEY, FIRMWARE_KEY
from printpi_daemon.fake_printer import DEFAULT_FIRMWARE_NAME, FLASHED_FIRMWARE_NAME, FakePrinter
from printpi_daemon.firmware import AvrdudeOutput, FirmwareError, FirmwareUpdater, list_files, parse_file_list
from printpi_daemon.printer import Printer, PrinterError
from tests.test_bridge import FAST, drain, make_bridge, wait_for


@pytest.fixture(autouse=True)
def fresh_fake():
    FakePrinter.next_firmware_name = None
    yield
    FakePrinter.next_firmware_name = None


@pytest.fixture
def printer():
    p = Printer(FAST, connect_timeout=1.0, ok_timeout=2.0)
    p.connect()
    yield p
    if p.connected:
        p.disconnect()


def make_updater(printer_ref, **overrides) -> FirmwareUpdater:
    """An updater on a Printer held in a one-element list, connecting the way the bridge does.

    Tests that put the fake behind a device path get it back on fake:// for the reconnect.
    """

    def connect() -> None:
        printer_ref[0].port_url = FAST
        if not printer_ref[0].connected:
            printer_ref[0].connect()

    def disconnect() -> None:
        printer_ref[0].disconnect()

    options = dict(printer=lambda: printer_ref[0], connect=connect, disconnect=disconnect, sleep=lambda s: None,
                   settle=0.0, vanish_timeout=0.2, reboot_timeout=1.0, reconnect_timeout=5.0, retry_interval=0.05)
    options.update(overrides)
    return FirmwareUpdater(**options)


def finished(updater: FirmwareUpdater, timeout: float = 10.0) -> dict:
    assert wait_for(lambda: updater.status()["phase"] in ("done", "failed"), timeout), updater.status()
    return updater.status()


# ---- file listing --------------------------------------------------------------------


def test_parse_file_list_reads_marlin_and_buddy_forms():
    lines = [
        "Begin file list",
        "CUBE~1.GCO 1048576",
        "FW~1.HEX 123 \"Firmware 3.14.1.hex\"",
        "SUBDIR/",
        "MK4_MK~1.BBF",
        "echo:busy: processing",
        "End file list",
        "ok",
    ]
    assert parse_file_list(lines) == [
        {"name": "CUBE~1.GCO", "size": 1048576, "long_name": None},
        {"name": "FW~1.HEX", "size": 123, "long_name": "Firmware 3.14.1.hex"},
        {"name": "MK4_MK~1.BBF", "size": None, "long_name": None},
    ]


def test_parse_file_list_needs_the_begin_marker():
    assert parse_file_list(['echo:Unknown command: "M20"']) == []
    assert parse_file_list(["CUBE~1.GCO 12"]) == []


def test_list_files_asks_the_printer(printer):
    files = list_files(printer)
    assert [entry["name"] for entry in files] == [name for name, _ in fake_printer.DRIVE_FILES]
    assert files[0]["size"] == fake_printer.DRIVE_FILES[0][1]


# ---- buddy and restart -------------------------------------------------------------


def test_buddy_flash_reboots_and_comes_back_with_the_new_firmware(printer):
    ref = [printer]
    statuses = []
    updater = make_updater(ref, on_status=statuses.append)
    status = updater.start("buddy", file="MK4_MK~1.BBF")
    assert status["phase"] == "preparing"
    assert status["firmware_before"] == DEFAULT_FIRMWARE_NAME

    status = finished(updater)
    assert status["phase"] == "done", status
    assert status["firmware_after"] == FLASHED_FIRMWARE_NAME
    assert status["file"] == "MK4_MK~1.BBF"
    assert status["error"] is None
    assert printer.connected
    assert printer.state.firmware["FIRMWARE_NAME"] == FLASHED_FIRMWARE_NAME
    assert "> M997 /usb/MK4_MK~1.BBF" in status["log"]
    phases = [entry["phase"] for entry in statuses]
    assert phases[0] == "preparing"
    assert phases.index("flashing") < phases.index("rebooting") < phases.index("reconnecting") < phases.index("done")


def test_restart_keeps_the_firmware(printer):
    updater = make_updater([printer])
    updater.start("restart")
    status = finished(updater)
    assert status["phase"] == "done"
    assert status["firmware_after"] == DEFAULT_FIRMWARE_NAME
    assert printer.connected
    assert "> M997" in status["log"]


def test_buddy_flash_waits_for_the_device_node_to_go_and_come_back(printer):
    node = {"present": True, "checks": 0}

    def port_exists(path: str) -> bool:
        node["checks"] += 1
        if node["checks"] == 2:
            node["present"] = False  # gone on the second look, back on the third
        elif node["checks"] == 3:
            node["present"] = True
        return node["present"]

    printer.port_url = "/dev/ttyACM0"  # the fake behind a device path
    updater = make_updater([printer], port_exists=port_exists)
    updater.start("restart")
    status = finished(updater)
    assert status["phase"] == "done", status
    assert "/dev/ttyACM0 is gone, the board is rebooting" in status["log"]
    assert "/dev/ttyACM0 is back" in status["log"]


def test_buddy_flash_fails_when_the_port_never_returns(printer):
    printer.port_url = "/dev/ttyACM0"
    calls = {"n": 0}

    def port_exists(path: str) -> bool:
        calls["n"] += 1
        return calls["n"] == 1  # present once, then gone for good

    updater = make_updater([printer], port_exists=port_exists, reboot_timeout=0.2)
    updater.start("restart")
    status = finished(updater)
    assert status["phase"] == "failed"
    assert "did not come back" in status["error"]


def test_reconnect_retries_until_the_board_answers(printer):
    ref = [printer]
    attempts = {"n": 0}

    def flaky_connect() -> None:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise PrinterError("could not open /dev/ttyACM0")
        if not ref[0].connected:
            ref[0].connect()

    updater = make_updater(ref, connect=flaky_connect)
    updater.start("restart")
    status = finished(updater)
    assert status["phase"] == "done", status
    assert attempts["n"] == 3
    assert sum("connect failed" in line for line in status["log"]) == 2


def test_reconnect_gives_up_after_the_timeout(printer):
    def never() -> None:
        raise PrinterError("could not open /dev/ttyACM0")

    updater = make_updater([printer], connect=never, reconnect_timeout=0.1)
    updater.start("restart")
    status = finished(updater)
    assert status["phase"] == "failed"
    assert "did not answer" in status["error"]


@pytest.mark.parametrize("method, kwargs, message", [
    ("buddy", {}, "USB drive is required"),
    ("buddy", {"file": "../etc/passwd"}, "USB drive is required"),
    ("buddy", {"file": "FIRMWARE.HEX"}, "end with .bbf"),
    ("bogus", {}, "unknown firmware method"),
    ("avrdude", {"file": "/nonexistent/firmware.hex"}, "does not exist"),
])
def test_start_refuses_bad_requests(printer, method, kwargs, message):
    updater = make_updater([printer])
    with pytest.raises(FirmwareError, match=message):
        updater.start(method, **kwargs)
    assert updater.status()["phase"] == "idle"


def test_start_refuses_without_a_connection():
    p = Printer(FAST)
    updater = make_updater([p])
    with pytest.raises(FirmwareError, match="not connected"):
        updater.start("buddy", file="MK4_MK~1.BBF")


def test_only_one_update_runs_at_a_time(printer):
    updater = make_updater([printer], reconnect_timeout=0.5, connect=lambda: time.sleep(0.1))
    updater.start("restart")
    with pytest.raises(FirmwareError, match="already running"):
        updater.start("restart")
    finished(updater)


# ---- avrdude -------------------------------------------------------------------------

AVRDUDE_RUN = (
    b"avrdude: AVR device initialized and ready to accept instructions\n"
    b"avrdude: reading input file \"/tmp/fw.hex\"\n"
    b"avrdude: writing flash (240000 bytes):\n"
    b"\nWriting | ###" + b"#" * 22 + b"\r" + b"Writing | " + b"#" * 50 + b" | 100% 4.53s\n\n"
    b"avrdude: verifying flash memory against /tmp/fw.hex:\n"
    b"\nReading | " + b"#" * 50 + b" | 100% 3.10s\n\n"
    b"avrdude: 240000 bytes of flash verified\n"
    b"avrdude done.  Thank you.\n"
)


class FakeProcess:
    def __init__(self, output: bytes, code: int = 0) -> None:
        self.stdout = io.BytesIO(output)
        self.code = code

    def wait(self) -> int:
        return self.code


def test_avrdude_output_reports_stages_and_progress():
    lines, progress = [], []
    output = AvrdudeOutput(on_line=lines.append, on_progress=lambda stage, value: progress.append((stage, value)))
    for i in range(0, len(AVRDUDE_RUN), 7):
        output.feed(AVRDUDE_RUN[i:i + 7])
    output.close()
    assert lines[0].startswith("avrdude: AVR device initialized")
    assert "Writing | " + "#" * 50 + " | 100% 4.53s" in lines
    assert lines[-1] == "avrdude done.  Thank you."
    assert progress[0] == ("Reading the file", 0.0)
    assert ("Writing flash", 0.5) in progress
    assert ("Writing flash", 1.0) in progress
    assert ("Verifying flash", 1.0) in progress
    assert progress[-1] == ("Flash verified", 0.0)


def test_avrdude_flashes_and_reconnects(printer, tmp_path):
    hex_file = tmp_path / "firmware.hex"
    hex_file.write_text(":00000001FF\n")
    printer.port_url = "/dev/ttyUSB0"
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        return FakeProcess(AVRDUDE_RUN)

    updater = make_updater([printer], run=run, which=lambda name: "/usr/bin/avrdude")
    updater.start("avrdude", file=str(hex_file), mcu="atmega2560", programmer="wiring", baud=115200)
    status = finished(updater)
    assert status["phase"] == "done", status
    assert calls == [["/usr/bin/avrdude", "-p", "atmega2560", "-c", "wiring", "-P", "/dev/ttyUSB0", "-b", "115200",
                      "-D", "-U", f"flash:w:{hex_file}:i"]]
    assert status["file"] == "firmware.hex"
    assert "avrdude: 240000 bytes of flash verified" in status["log"]
    assert printer.connected


def test_avrdude_failure_names_the_last_line(printer, tmp_path):
    hex_file = tmp_path / "firmware.hex"
    hex_file.write_text(":00000001FF\n")
    printer.port_url = "/dev/ttyUSB0"
    output = b"avrdude: stk500v2_ReceiveMessage(): timeout\navrdude: stk500v2_getsync(): timeout communicating with programmer\n"
    updater = make_updater([printer], run=lambda args, **kwargs: FakeProcess(output, code=1), which=lambda name: "/usr/bin/avrdude")
    updater.start("avrdude", file=str(hex_file))
    status = finished(updater)
    assert status["phase"] == "failed"
    assert status["error"] == "avrdude exited with status 1: avrdude: stk500v2_getsync(): timeout communicating with programmer"


def test_avrdude_must_be_installed(printer, tmp_path):
    hex_file = tmp_path / "firmware.hex"
    hex_file.write_text(":00000001FF\n")
    printer.port_url = "/dev/ttyUSB0"
    updater = make_updater([printer], which=lambda name: None)
    updater.start("avrdude", file=str(hex_file))
    status = finished(updater)
    assert status["phase"] == "failed"
    assert status["error"] == "avrdude is not installed on this host"
    assert status["avrdude_available"] is False


def test_avrdude_needs_a_device_path(printer, tmp_path):
    hex_file = tmp_path / "firmware.hex"
    hex_file.write_text(":00000001FF\n")
    updater = make_updater([printer])
    with pytest.raises(FirmwareError, match="local serial port"):
        updater.start("avrdude", file=str(hex_file))


# ---- bridge --------------------------------------------------------------------------


@pytest.fixture
def bridge():
    b = make_bridge()
    b.firmware._sleep = lambda s: None
    b.firmware.settle = 0.0
    b.firmware.retry_interval = 0.05
    yield b
    b.jobs.stop()
    if b.printer.connected:
        b.printer.disconnect()


def run_worker_calls(bridge) -> None:
    """The worker thread is not running in these tests; execute what the updater queued."""
    while not bridge._commands.empty():
        bridge._execute(bridge._commands.get_nowait())


def test_firmware_files_command_writes_the_listing(bridge):
    bridge._execute({"type": "connect"})
    bridge._execute({"type": "firmware_files"})
    listings = [payload for channel, payload in drain(bridge) if channel == FIRMWARE_FILES_KEY]
    assert listings[-1]["error"] is None
    assert [entry["name"] for entry in listings[-1]["files"]] == ["MK4_MK~1.BBF", "CUBE~1.GCO"]


def test_firmware_files_without_a_printer_records_the_error(bridge):
    with pytest.raises(PrinterError):
        bridge._execute({"type": "firmware_files"})
    listings = [payload for channel, payload in drain(bridge) if channel == FIRMWARE_FILES_KEY]
    assert listings[-1]["files"] == []
    assert listings[-1]["error"] == "not connected"


def test_firmware_flash_command_runs_the_update_through_the_worker(bridge):
    bridge._execute({"type": "connect"})
    bridge._execute({"type": "firmware_flash", "method": "buddy", "file": "MK4_MK~1.BBF"})
    events = [payload for channel, payload in drain(bridge) if channel == EVENTS_CHANNEL]
    assert events[-1] == {"type": "firmware_flash", "method": "buddy", "file": "MK4_MK~1.BBF", "t": events[-1]["t"]}
    # The reconnect is queued for the worker, which this test drives by hand.
    deadline = time.monotonic() + 10
    while bridge.firmware.status()["phase"] not in ("done", "failed") and time.monotonic() < deadline:
        run_worker_calls(bridge)
        time.sleep(0.02)
    status = bridge.firmware.status()
    assert status["phase"] == "done", status
    assert status["firmware_after"] == FLASHED_FIRMWARE_NAME
    assert bridge.printer.connected
    written = [payload for channel, payload in drain(bridge) if channel == FIRMWARE_KEY]
    assert written[-1]["phase"] == "done"


def test_firmware_flash_is_refused_during_a_print(bridge, tmp_path):
    gcode = tmp_path / "part.gcode"
    gcode.write_text("G28\n" + "G1 X1\n" * 200)
    bridge._execute({"type": "connect"})
    bridge._execute({"type": "print_start", "path": str(gcode), "name": "part.gcode"})
    try:
        with pytest.raises(FirmwareError, match="while a print is active"):
            bridge._execute({"type": "firmware_flash", "method": "restart"})
        assert bridge.firmware.status()["phase"] == "idle"
    finally:
        bridge.jobs.cancel()
        wait_for(lambda: not bridge.jobs.state.active, 10)


def test_firmware_flash_rejects_a_bad_method(bridge):
    bridge._execute({"type": "connect"})
    with pytest.raises(FirmwareError, match="unknown firmware method"):
        bridge._execute({"type": "firmware_flash", "method": "dfu"})


def test_heartbeat_status_is_idle_and_serialisable(bridge):
    status = bridge.firmware.status()
    assert status["phase"] == "idle"
    assert isinstance(status["avrdude_available"], bool)
    json.dumps(status)
