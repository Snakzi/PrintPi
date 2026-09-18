from printpi_daemon import protocol


def test_checksum_matches_marlin_example():
    assert protocol.checksum("N12 G1 X10") == 98


def test_format_line_with_number_and_checksum():
    assert protocol.format_line("G1 X10 ; move", 12) == "N12 G1 X10*98"


def test_format_line_without_number_strips_comment():
    assert protocol.format_line("G28 ; home") == "G28"


def test_plain_ok():
    msg = protocol.parse("ok")
    assert msg.is_ok and not msg.temperatures


def test_advanced_ok_is_still_ok():
    assert protocol.parse("ok N5 P15 B3").is_ok


def test_ok_with_temperatures():
    msg = protocol.parse("ok T:210.00 /210.00 B:60.00 /60.00 @:127 B@:0")
    assert msg.is_ok
    assert msg.temperatures == {"T0": (210.0, 210.0), "B": (60.0, 60.0)}


def test_autoreport_temperature_line():
    msg = protocol.parse(" T:22.50 /0.00 B:22.66 /0.00 @:0 B@:0")
    assert msg.kind == "temperature"
    assert msg.temperatures["T0"] == (22.5, 0.0)
    assert msg.temperatures["B"] == (22.66, 0.0)


def test_multi_extruder_and_wait_marker():
    msg = protocol.parse("T:150.32 /200.00 B:45.11 /60.00 T0:150.32 /200.00 T1:30.00 /0.00 @:127 B@:0 W:?")
    assert msg.temperatures["T1"] == (30.0, 0.0)
    assert "W" not in msg.temperatures
    assert msg.waiting
    assert not protocol.parse(" T:22.50 /0.00 B:22.66 /0.00 @:0 B@:0").waiting


def test_resend_variants():
    assert protocol.parse("Resend: 5").resend_line == 5
    assert protocol.parse("Resend:5").resend_line == 5
    assert protocol.parse("rs 5").resend_line == 5


def test_error_line():
    msg = protocol.parse("Error:checksum mismatch, Last Line: 4")
    assert msg.kind == "error"
    assert msg.error == "checksum mismatch, Last Line: 4"


def test_busy_and_wait():
    assert protocol.parse("echo:busy: processing").kind == "busy"
    assert protocol.parse("wait").kind == "wait"


def test_start():
    assert protocol.parse("start").kind == "start"


def test_firmware_line_is_not_mistaken_for_temperatures():
    msg = protocol.parse(
        "FIRMWARE_NAME:Marlin 2.1.2 (Sep 14 2026) SOURCE_CODE_URL:github.com/MarlinFirmware/Marlin"
        " PROTOCOL_VERSION:1.0 MACHINE_TYPE:Ender-3 EXTRUDER_COUNT:1 UUID:cede2a2f"
    )
    assert msg.kind == "firmware"
    assert not msg.temperatures
    assert msg.firmware["FIRMWARE_NAME"] == "Marlin 2.1.2 (Sep 14 2026)"
    assert msg.firmware["MACHINE_TYPE"] == "Ender-3"
    assert msg.firmware["EXTRUDER_COUNT"] == "1"


def test_capability():
    assert protocol.parse("Cap:AUTOREPORT_TEMP:1").capability == ("AUTOREPORT_TEMP", True)
    assert protocol.parse("Cap:PROGRESS:0").capability == ("PROGRESS", False)


def test_position_report():
    msg = protocol.parse("X:10.00 Y:20.50 Z:0.30 E:1.00 Count X:800 Y:1640 Z:120")
    assert msg.kind == "position"
    assert msg.position == {"X": 10.0, "Y": 20.5, "Z": 0.3, "E": 1.0}


def test_echo_and_other():
    assert protocol.parse('echo:Unknown command: "M999"').kind == "echo"
    assert protocol.parse("Begin file list").kind == "other"


def test_prusa_buddy_temperature_report():
    msg = protocol.parse("ok T:25.00/0.00 B:22.35/0.00 X:22.48/36.00 A:31.98/0.00 @:0 B@:0 HBR@:0")
    assert msg.is_ok
    assert msg.temperatures["T0"] == (25.0, 0.0)
    assert msg.temperatures["B"] == (22.35, 0.0)
    assert msg.temperatures["X"] == (22.48, 36.0)
    assert msg.temperatures["A"] == (31.98, 0.0)
    assert "HBR" not in msg.temperatures
