"""Marlin serial line protocol.

Outgoing lines get a line number and an XOR checksum ("N12 G1 X10*98"), incoming
lines are classified into Message objects. Pure functions without I/O, so all of
this is unit-testable without a printer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# " T:210.00 /210.00 B:60.00 /60.00 @:127 B@:0"  ->  sensor, actual, optional target
# Prusa Buddy adds X (heatbreak) and A (ambient/board) and writes "T:25.00/0.00" without spaces.
_TEMP_RE = re.compile(
    r"(?P<sensor>B|C|A|P|R|L|X|T\d*)\s*:\s*(?P<actual>-?\d+(?:\.\d+)?)"
    r"(?:\s*/\s*(?P<target>-?\d+(?:\.\d+)?))?"
)
# Only lines that start like a temperature report are parsed for temperatures,
# otherwise "EXTRUDER_COUNT:1" in the M115 reply would look like sensor T=1.
_TEMP_LINE_RE = re.compile(r"^(?:ok\s+)?(?:T\d*|B|C)\s*:")
_RESEND_RE = re.compile(r"^(?:Resend|rs)\s*:?\s*(?P<line>\d+)", re.IGNORECASE)
_POSITION_RE = re.compile(r"(?P<axis>[XYZE])\s*:\s*(?P<value>-?\d+(?:\.\d+)?)")
_FIRMWARE_RE = re.compile(r"(?P<key>[A-Z][A-Z_]+):(?P<value>.*?)(?=\s+[A-Z][A-Z_]+:|$)")
_CAP_RE = re.compile(r"^Cap:(?P<name>[A-Z_0-9]+):(?P<value>[01])")
# Host action commands: "// action:pause" from Marlin and Buddy, "//action:paused" from the MK3.
_ACTION_RE = re.compile(r"^//\s*action:\s*(?P<name>[a-z_]+)(?:\s+(?P<params>.*))?$", re.IGNORECASE)


def checksum(line: str) -> int:
    """XOR of all bytes, the way Marlin verifies "N<n> <command>*<checksum>"."""
    result = 0
    for byte in line.encode("ascii", "replace"):
        result ^= byte
    return result & 0xFF


def strip_comment(line: str) -> str:
    """Remove a trailing ";" comment and surrounding whitespace."""
    index = line.find(";")
    if index >= 0:
        line = line[:index]
    return line.strip()


def format_line(command: str, line_number: int | None = None) -> str:
    """Build the wire form of a command, with line number and checksum if requested."""
    command = strip_comment(command)
    if line_number is None:
        return command
    body = f"N{line_number} {command}"
    return f"{body}*{checksum(body)}"


@dataclass
class Message:
    """One parsed line from the printer."""

    raw: str
    kind: str = "other"
    # {"T0": (actual, target), "B": (actual, target)}; target is None when not reported
    temperatures: dict[str, tuple[float, float | None]] = field(default_factory=dict)
    resend_line: int | None = None
    position: dict[str, float] = field(default_factory=dict)
    firmware: dict[str, str] = field(default_factory=dict)
    capability: tuple[str, bool] | None = None
    error: str | None = None
    # A temperature report with "W:" is Marlin's heartbeat while M109/M190 wait for a heater.
    waiting: bool = False
    action: str | None = None  # a host action command the printer sent: pause, resume, cancel ...

    @property
    def is_ok(self) -> bool:
        return self.kind == "ok"


def parse(raw: str) -> Message:
    """Classify a line received from the printer."""
    line = raw.strip()
    msg = Message(raw=raw)

    if not line:
        msg.kind = "empty"
        return msg
    if line == "start":
        msg.kind = "start"
        return msg
    if line == "ok" or line.startswith("ok "):
        msg.kind = "ok"
        if _TEMP_LINE_RE.match(line):
            msg.temperatures = _parse_temperatures(line[2:])
        return msg

    action = _ACTION_RE.match(line)
    if action:
        msg.kind = "action"
        msg.action = action.group("name").lower()
        return msg
    resend = _RESEND_RE.match(line)
    if resend:
        msg.kind = "resend"
        msg.resend_line = int(resend.group("line"))
        return msg
    if line.startswith("Error:") or line.startswith("!!"):
        msg.kind = "error"
        msg.error = line.split(":", 1)[1].strip() if line.startswith("Error:") else line
        return msg
    if line.startswith("echo:busy:"):
        msg.kind = "busy"
        return msg
    if line == "wait":
        msg.kind = "wait"
        return msg
    if _TEMP_LINE_RE.match(line):
        msg.kind = "temperature"
        msg.temperatures = _parse_temperatures(line)
        msg.waiting = " W:" in line
        return msg
    if line.startswith("X:") and "Y:" in line:
        msg.kind = "position"
        msg.position = _parse_position(line)
        return msg
    if line.startswith("FIRMWARE_NAME:"):
        msg.kind = "firmware"
        msg.firmware = {key: value.strip() for key, value in _FIRMWARE_RE.findall(line)}
        return msg
    cap = _CAP_RE.match(line)
    if cap:
        msg.kind = "capability"
        msg.capability = (cap.group("name"), cap.group("value") == "1")
        return msg
    if line.startswith("echo:"):
        msg.kind = "echo"
        return msg
    return msg


def _parse_temperatures(text: str) -> dict[str, tuple[float, float | None]]:
    result: dict[str, tuple[float, float | None]] = {}
    for match in _TEMP_RE.finditer(text):
        sensor = match.group("sensor")
        if sensor == "T":
            sensor = "T0"
        target = match.group("target")
        result[sensor] = (float(match.group("actual")), float(target) if target is not None else None)
    return result


def _parse_position(text: str) -> dict[str, float]:
    # M114 reports "X:0.00 Y:0.00 Z:0.00 E:0.00 Count X:0 Y:0 Z:0"; keep the first
    # set of values, which are the logical positions.
    text = text.split("Count", 1)[0]
    return {axis: float(value) for axis, value in _POSITION_RE.findall(text)}
