import time

import pytest

from printpi_daemon.printer import CommandTimeout, NotConnected, Printer, PrinterHalted

FAST = "fake://?time_scale=0.01"


def wait_for(predicate, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


@pytest.fixture
def printer():
    p = Printer(FAST, connect_timeout=1.0, ok_timeout=2.0, temperature_interval=1.0)
    yield p
    if p._port is not None:
        p.disconnect()


def fake_of(printer: Printer):
    return printer._port


def test_connect_handshake(printer):
    states = []
    printer.on_state = lambda s: states.append(s.connection)
    printer.connect()
    assert printer.connected
    assert printer.state.firmware["FIRMWARE_NAME"].startswith("Marlin")
    assert printer.state.capabilities["AUTOREPORT_TEMP"] is True
    assert printer.state.temperatures["T0"].actual == pytest.approx(22.0)
    assert fake_of(printer).commands[:2] == ["M110 N0", "M115"]
    assert "connecting" in states and states[-1] == "connected"


def test_send_returns_response_lines(printer):
    printer.connect()
    lines = printer.send("M115")
    assert lines[0].startswith("FIRMWARE_NAME:")
    assert lines[-1] == "Cap:SDCARD:1"


def test_g28_updates_position_and_status(printer):
    printer.connect()
    fake_of(printer).position.update({"X": 30.0, "Y": 30.0})
    printer.send("G28")
    assert printer.state.position == {"X": 0.0, "Y": 0.0, "Z": 0.0, "E": 0.0}
    assert printer.state.status == "idle"


def test_line_numbers_increase(printer):
    printer.connect()
    before = fake_of(printer).last_line
    printer.send("G91")
    printer.send("G90")
    assert fake_of(printer).last_line == before + 2


def test_resend_is_handled_transparently():
    printer = Printer(FAST + "&resend_every=3", connect_timeout=1.0, ok_timeout=2.0)
    printer.connect()
    try:
        for _ in range(10):
            printer.send("M114")
        commands = fake_of(printer).commands
        assert commands.count("M114") == 10
        assert fake_of(printer).last_line == printer._line_number - 1
    finally:
        printer.disconnect()


def test_autoreport_updates_temperatures(printer):
    printer.connect()
    printer.send("M104 S200")
    assert wait_for(lambda: (printer.state.temperatures["T0"].target or 0) == 200)
    assert wait_for(lambda: printer.state.temperatures["T0"].actual > 100, timeout=3.0)


def test_polling_when_firmware_has_no_autoreport(printer):
    printer.connect()
    assert "M155 S1" in fake_of(printer).commands


def test_busy_extends_timeout():
    printer = Printer(FAST, connect_timeout=1.0, ok_timeout=0.05)
    printer.connect()
    try:
        # G28 takes 3 simulated seconds with busy keepalives in between, far more
        # than the ok timeout; the keepalives must keep the command alive.
        printer.send("G28")
    finally:
        printer.disconnect()


def test_heating_reports_extend_timeout():
    printer = Printer(FAST, connect_timeout=1.0, ok_timeout=0.1)
    printer.connect()
    try:
        # M109 reports "T:... W:?" once a simulated second while it heats and
        # sends no busy keepalive; reaching 200 °C takes far longer than the timeout.
        printer.send("M109 S200")
        assert printer.state.temperatures["T0"].actual == pytest.approx(200.0, abs=2.5)
    finally:
        printer.disconnect()


def test_timeout_disconnects():
    printer = Printer(FAST, connect_timeout=1.0, ok_timeout=0.1)
    printer.connect()
    fake_of(printer).latency = 0.5
    with pytest.raises(CommandTimeout):
        printer.send("M114")
    assert printer.state.connection == "error"
    assert "timeout" in (printer.state.last_error or "")


def test_emergency_stop_halts(printer):
    printer.connect()
    printer.emergency_stop()
    assert wait_for(lambda: printer.state.status == "halted")
    with pytest.raises(PrinterHalted):
        printer.send("G28")


def test_disconnect_and_reconnect(printer):
    printer.connect()
    printer.disconnect()
    assert printer.state.connection == "offline"
    with pytest.raises(NotConnected):
        printer.send("G28")
    printer.connect()
    assert printer.connected


def test_unexpected_reset_drops_connection(printer):
    printer.connect()
    fake_of(printer).dtr = False
    fake_of(printer).dtr = True
    assert wait_for(lambda: printer.state.connection == "error")
    assert "reset" in printer.state.last_error


def test_line_listener_sees_both_directions(printer):
    seen = []
    printer.on_line = lambda direction, line: seen.append((direction, line))
    printer.connect()
    assert ("tx", "N0 M110 N0*125") in seen
    assert ("rx", "start") in seen


def test_a_lost_line_is_recovered_through_a_probe():
    # Every 7th line vanishes on the way to the printer, which therefore never asks for
    # a resend. The probe with the next line number makes it ask, and streaming goes on.
    printer = Printer(FAST + "&drop_every=7", connect_timeout=1.0, ok_timeout=2.0, probe_timeout=0.1)
    printer.connect()
    try:
        for _ in range(20):
            printer.send("M114")
        fake = fake_of(printer)
        assert fake.commands.count("M114") == 20
        assert fake.last_line == printer._line_number - 1
        assert "M105" in fake.commands  # the probe was accepted after the lost line was resent
        assert printer.state.connection == "connected"
    finally:
        printer.disconnect()


def test_a_lost_ok_is_recovered_through_a_probe():
    printer = Printer(FAST + "&drop_ok_every=5", connect_timeout=1.0, ok_timeout=2.0, probe_timeout=0.1)
    printer.connect()
    try:
        for _ in range(12):
            printer.send("M114")
        fake = fake_of(printer)
        assert fake.commands.count("M114") == 12
        assert fake.last_line == printer._line_number - 1
        # Nothing is left pending once the probe's "ok T:..." settled the missing ok.
        assert not printer._expect
    finally:
        printer.disconnect()


def test_a_slow_printer_survives_a_probe_and_keeps_its_replies():
    printer = Printer(FAST, connect_timeout=1.0, ok_timeout=2.0, probe_timeout=0.1)
    printer.connect()
    try:
        fake_of(printer).latency = 0.25
        reply = printer.send("M115")
        assert any(line.startswith("FIRMWARE_NAME:") for line in reply)
        position = printer.send("M114")
        assert any(line.startswith("X:") for line in position)
        assert wait_for(lambda: not printer._expect)
        assert fake_of(printer).last_line == printer._line_number - 1
    finally:
        printer.disconnect()


def test_probing_can_be_switched_off():
    # The handshake takes four lines, so the sixth is the second M114.
    printer = Printer(FAST + "&drop_every=6", connect_timeout=1.0, ok_timeout=0.3, probe_timeout=None)
    printer.connect()
    fake = fake_of(printer)  # the timeout closes the port, so keep the fake
    handshake = len(fake.commands)
    with pytest.raises(CommandTimeout):
        for _ in range(5):
            printer.send("M114")
    assert fake.commands[handshake:] == ["M114"]



def test_busy_keepalives_hold_the_probe_back():
    # G28 takes 3 simulated seconds and reports busy every 2; with a probe timeout in between
    # the keepalive must push the probe out again and again, so none is sent.
    sent: list[str] = []
    printer = Printer("fake://?time_scale=0.1", connect_timeout=1.0, ok_timeout=5.0, probe_timeout=0.25,
                      on_line=lambda direction, line: sent.append(line) if direction == "tx" else None)
    printer.connect()
    try:
        before = len(sent)
        printer.send("G28")
        assert not any("M105" in line for line in sent[before:])
    finally:
        printer.disconnect()


def test_a_silent_printer_gets_at_most_two_probes():
    sent: list[str] = []
    printer = Printer(FAST, connect_timeout=1.0, ok_timeout=3.0, probe_timeout=0.1,
                      on_line=lambda direction, line: sent.append(line) if direction == "tx" else None)
    printer.connect()
    try:
        fake_of(printer).latency = 1.2  # answers nothing for longer than several probe timeouts
        before = len(sent)
        printer.send("M114")
        assert sum("M105" in line for line in sent[before:]) == 2
    finally:
        printer.disconnect()
