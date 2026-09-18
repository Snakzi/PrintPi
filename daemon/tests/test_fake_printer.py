import time

import pytest

from printpi_daemon.fake_printer import FakePrinter
from printpi_daemon.protocol import format_line

_buffers: dict[int, bytes] = {}
BOOT_LINES = 7  # "start" plus six lines of chatter


def read_lines(printer: FakePrinter, count: int, timeout: float = 2.0) -> list[str]:
    """Read up to `count` complete lines, keeping leftover bytes for the next call."""
    lines: list[str] = []
    buffer = _buffers.get(id(printer), b"")
    deadline = time.monotonic() + timeout
    while len(lines) < count:
        while b"\n" in buffer and len(lines) < count:
            line, buffer = buffer.split(b"\n", 1)
            lines.append(line.decode())
        if len(lines) >= count or time.monotonic() >= deadline:
            break
        data = printer.read(max(1, printer.in_waiting))
        if data:
            buffer += data
    _buffers[id(printer)] = buffer
    return lines


def wait_until_ok(printer: FakePrinter, timeout: float = 5.0) -> list[str]:
    lines: list[str] = []
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        got = read_lines(printer, 1, timeout=min(0.5, max(0.0, deadline - time.monotonic())))
        if not got:
            continue
        lines += got
        if got[0].startswith("ok"):
            return lines
    raise AssertionError(f"no ok within {timeout}s, got {lines}")


def send(printer: FakePrinter, command: str, number: int | None = None) -> list[str]:
    printer.write((format_line(command, number) + "\n").encode())
    return wait_until_ok(printer)


def boot(printer: FakePrinter) -> list[str]:
    lines = read_lines(printer, BOOT_LINES)
    assert lines and lines[0] == "start", lines
    return lines


@pytest.fixture
def fake():
    printer = FakePrinter(time_scale=0.01, boot_delay=0.0)
    printer.timeout = 0.2
    boot(printer)
    yield printer
    printer.close()
    _buffers.pop(id(printer), None)


def test_boot_chatter_ends_with_sd_message():
    printer = FakePrinter(time_scale=0.01, boot_delay=0.0)
    try:
        lines = boot(printer)
        assert lines[1].startswith("echo:Marlin")
        assert lines[-1] == "echo:SD init fail"
    finally:
        printer.close()


def test_m105_reports_temperatures(fake):
    lines = send(fake, "M105")
    assert lines[-1].startswith("ok T:22.00 /0.00 B:22.00 /0.00")


def test_unknown_command_is_echoed(fake):
    lines = send(fake, "M999")
    assert lines == ['echo:Unknown command: "M999"', "ok"]


def test_line_numbers_and_checksums(fake):
    send(fake, "M110 N0", 0)
    lines = send(fake, "G28", 1)
    assert lines[-1] == "ok"
    assert fake.last_line == 1


def test_bad_checksum_requests_resend(fake):
    send(fake, "M110 N0", 0)
    fake.write(b"N1 G28*1\n")
    lines = wait_until_ok(fake)
    assert lines == ["Error:checksum mismatch, Last Line: 0", "Resend: 1", "ok"]
    assert "G28" not in fake.commands


def test_line_number_gap_requests_resend(fake):
    send(fake, "M110 N0", 0)
    lines = send(fake, "G28", 5)
    assert lines[0].startswith("Error:Line Number is not Last Line Number+1")
    assert lines[1] == "Resend: 1"


def test_injected_resend_only_once_per_line(fake):
    fake.resend_every = 2
    send(fake, "M110 N0", 0)  # line 1 received
    lines = send(fake, "G28", 1)  # line 2 received: injected resend
    assert lines[1] == "Resend: 1"
    lines = send(fake, "G28", 1)  # the resent line is accepted
    assert lines[-1] == "ok"
    assert fake.commands.count("G28") == 1


def test_g28_homes_and_reports_position(fake):
    fake.position.update({"X": 50.0, "Y": 50.0, "Z": 10.0})
    lines = send(fake, "G28")
    assert any(line.startswith("echo:busy") for line in lines)
    assert lines[-2].startswith("X:0.00 Y:0.00 Z:0.00")
    assert fake.homed


def test_relative_moves(fake):
    send(fake, "G91")
    send(fake, "G1 X10 F6000")
    send(fake, "G1 X5")
    assert fake.position["X"] == 15.0


def test_heating_drifts_towards_target(fake):
    send(fake, "M104 S200")
    time.sleep(0.3)  # 30 simulated seconds with time_scale 0.01
    lines = send(fake, "M105")
    actual = float(lines[-1].split("T:")[1].split()[0])
    assert 150 < actual < 200


def test_m109_waits_and_reports_progress(fake):
    lines = send(fake, "M109 S200")
    assert any("W:?" in line for line in lines)
    assert lines[-1] == "ok"
    assert fake.hotend.actual > 197


def test_m115_reports_firmware_and_capabilities(fake):
    lines = send(fake, "M115")
    assert lines[0].startswith("FIRMWARE_NAME:Marlin")
    assert "Cap:AUTOREPORT_TEMP:1" in lines


def test_autoreport(fake):
    send(fake, "M155 S1")
    lines = read_lines(fake, 2, timeout=1.0)
    assert len(lines) == 2
    assert all(line.startswith(" T:") for line in lines)


def test_m112_kills_immediately_and_reset_reboots(fake):
    fake.write(b"M112\n")
    assert read_lines(fake, 1)[0] == "Error:Printer halted. kill() called!"
    fake.write(b"M105\n")
    assert read_lines(fake, 1, timeout=0.3) == []
    fake.dtr = False
    fake.dtr = True
    boot(fake)
    assert send(fake, "M105")[-1].startswith("ok T:")


def test_from_url():
    printer = FakePrinter.from_url("fake://?time_scale=0.5&latency=0.01&resend_every=7")
    try:
        assert printer.time_scale == 0.5
        assert printer.latency == 0.01
        assert printer.resend_every == 7
    finally:
        printer.close()
