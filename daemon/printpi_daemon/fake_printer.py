"""A fake Marlin printer behind a serial-like interface.

Lets the daemon be developed and tested without hardware. It boots with "start",
answers M105 with temperatures that drift towards their targets, honours line
numbers and checksums (and asks for a Resend when they are wrong), takes a
realistic amount of time for homing and heating, and can inject faults.

URL form:  fake://?time_scale=1&latency=0.05&resend_every=20

  time_scale   1 = real time, 0.01 = a hundred times faster (for tests)
  latency      seconds added before every reply, simulates a slow link
  resend_every ask for a Resend on every n-th numbered line, 0 = never
  drop_every   lose every n-th numbered line on the way in, as if it never arrived
  drop_ok_every  execute every n-th numbered line but lose its "ok" on the way out
  firmware     buddy or prusa: report that firmware's name and pause like it does,
               M601 parks and M602 returns with the host actions each family sends

Differences to real Marlin worth knowing: commands are executed one after the
other and "ok" comes after execution. Real Marlin buffers a few moves and acks
them as soon as they are queued, so it streams faster than this fake.
"""

from __future__ import annotations

import math
import queue
import re
import threading
import time
from urllib.parse import parse_qs, urlparse

from .protocol import checksum

AMBIENT = 22.0
MESH_POINTS = 5
DEFAULT_FIRMWARE_NAME = "Marlin 2.1.2 (PrintPi fake)"
FIRMWARE_NAMES = {
    "buddy": "Prusa-Firmware-Buddy 6.5.7+12836 (PrintPi fake)",
    "prusa": "Prusa-Firmware 3.14.1 based on Marlin (PrintPi fake)",
}
# What the fake boots with after M997 "flashed" the firmware file from its drive.
FLASHED_FIRMWARE_NAME = "Marlin 2.1.3 (PrintPi fake)"
# What M20 lists: a firmware file as Buddy names it in 8.3 form, and a print.
DRIVE_FILES = (("MK4_MK~1.BBF", 4100840), ("CUBE~1.GCO", 1048576))
_LINE_RE = re.compile(r"^N(?P<n>\d+)\s+(?P<body>.*?)(?:\*(?P<cs>\d+))?$")
_PARAM_RE = re.compile(r"(?P<letter>[A-Z])(?P<value>-?\d*\.?\d*)")


def _bed_height(x: int, y: int) -> float:
    """A bed that is tilted towards the front left and sags a little in the middle."""
    centre = (MESH_POINTS - 1) / 2
    dx, dy = x - centre, y - centre
    return round(0.03 * dx - 0.02 * dy - 0.06 * (1 - (dx * dx + dy * dy) / (2 * centre * centre)), 3)


class _Heater:
    """First-order thermal model: approaches the target with time constant tau."""

    def __init__(self, clock, tau: float, max_temp: float) -> None:
        self._clock = clock
        self._stamp = clock()
        self.tau = tau
        self.max_temp = max_temp
        self.actual = AMBIENT
        self.target = 0.0

    def set_target(self, value: float) -> None:
        self.update()
        self.target = max(0.0, min(value, self.max_temp))

    def update(self) -> float:
        now = self._clock()
        dt = max(0.0, now - self._stamp)
        self._stamp = now
        goal = self.target if self.target > 0 else AMBIENT
        self.actual += (goal - self.actual) * (1 - math.exp(-dt / self.tau))
        return self.actual

    @property
    def heating(self) -> bool:
        return self.target > 0 and self.actual < self.target - 0.5

    def at_target(self, window: float = 2.0) -> bool:
        return abs(self.update() - self.target) <= window


class FakePrinter:
    # A firmware update outlives the instance: M997 vanishes like a rebooting USB
    # device and the next instance opened on fake:// boots with this name.
    next_firmware_name: str | None = None

    def __init__(
        self,
        *,
        time_scale: float = 1.0,
        latency: float = 0.0,
        resend_every: int = 0,
        drop_every: int = 0,
        drop_ok_every: int = 0,
        boot_delay: float = 0.3,
        firmware_name: str = DEFAULT_FIRMWARE_NAME,
        firmware: str | None = None,
    ) -> None:
        self.time_scale = max(1e-4, time_scale)
        self.latency = latency
        self.resend_every = resend_every
        self.drop_every = drop_every
        self.drop_ok_every = drop_ok_every
        self.boot_delay = boot_delay
        self.firmware = firmware  # None for plain Marlin, "buddy" or "prusa" for Prusa's pause behaviour
        self.firmware_name = FIRMWARE_NAMES.get(firmware or "", firmware_name)
        self.paused = False
        self.pause_delay = 0.5  # simulated seconds until the head is parked
        self.resume_delay = 2.0  # simulated seconds of reheating and returning; None = the host action never comes
        self.timeout: float = 1.0

        self._out = bytearray()
        self._out_cv = threading.Condition()
        self._in = bytearray()
        self._commands: queue.Queue[str | None] = queue.Queue()
        self._closed = False
        self._gone = False  # rebooted: reads and writes fail like on an unplugged device
        self._dtr = True
        self._model_lock = threading.Lock()
        self._command = ""  # the command being executed, for handlers that need its text

        clock = lambda: time.monotonic() / self.time_scale  # noqa: E731
        self.hotend = _Heater(clock, tau=8.0, max_temp=300.0)
        self.bed = _Heater(clock, tau=30.0, max_temp=120.0)
        self.position = {"X": 0.0, "Y": 0.0, "Z": 0.0, "E": 0.0}
        self.feedrate = 3000.0  # mm/min
        self.relative = False
        self.relative_e = False  # M83; G91 covers all axes like Marlin does
        self.homed = False
        self.mesh: list[list[float]] = []  # probed by G29, reported by M420 V
        self.halted = False
        self._break_wait = False
        self.last_line = 0
        self.autoreport_interval = 0.0
        self.lines_received = 0
        self._last_injected: int | None = None
        self._last_dropped: int | None = None
        self._swallow_ok = False
        # Commands as executed, without line number and checksum. Handy in tests.
        self.commands: list[str] = []

        self._boot()
        threading.Thread(target=self._run, name="fake-printer", daemon=True).start()
        threading.Thread(target=self._autoreport, name="fake-autoreport", daemon=True).start()

    @classmethod
    def from_url(cls, url: str) -> "FakePrinter":
        params = {key: values[-1] for key, values in parse_qs(urlparse(url).query).items()}
        return cls(
            time_scale=float(params.get("time_scale", 1.0)),
            latency=float(params.get("latency", 0.0)),
            resend_every=int(params.get("resend_every", 0)),
            drop_every=int(params.get("drop_every", 0)),
            drop_ok_every=int(params.get("drop_ok_every", 0)),
            firmware_name=cls.next_firmware_name or DEFAULT_FIRMWARE_NAME,
            firmware=params.get("firmware"),
        )

    # ---- serial-like interface -------------------------------------------------

    @property
    def in_waiting(self) -> int:
        with self._out_cv:
            return len(self._out)

    def read(self, size: int = 1) -> bytes:
        with self._out_cv:
            if not self._out and not self._closed and not self._gone:
                self._out_cv.wait(self.timeout)
            if not self._out and self._gone:
                raise OSError("device disconnected")
            data = bytes(self._out[:size])
            del self._out[:size]
            return data

    def write(self, data: bytes) -> int:
        if self._closed:
            raise OSError("port is closed")
        if self._gone:
            raise OSError("device disconnected")
        self._in += data
        while (index := self._in.find(b"\n")) >= 0:
            line = self._in[:index].decode("utf-8", errors="replace").strip()
            del self._in[: index + 1]
            if not line:
                continue
            # Marlin scans incoming bytes for M112 and kills immediately, even while
            # a long command is running; M108 breaks out of a heat-up the same way.
            if "M112" in line:
                self._kill()
                continue
            if "M108" in line:
                self._break_wait = True
                if not line.startswith("N"):
                    continue
            self._commands.put(line)
        return len(data)

    def close(self) -> None:
        self._closed = True
        self._commands.put(None)
        with self._out_cv:
            self._out_cv.notify_all()

    def flush(self) -> None:
        pass

    def reset_input_buffer(self) -> None:
        with self._out_cv:
            self._out.clear()

    def reset_output_buffer(self) -> None:
        self._in.clear()

    @property
    def dtr(self) -> bool:
        return self._dtr

    @dtr.setter
    def dtr(self, value: bool) -> None:
        # A rising edge on DTR resets Arduino-style boards.
        if value and not self._dtr:
            self.reset()
        self._dtr = value

    # ---- printer model -----------------------------------------------------------

    def reset(self) -> None:
        with self._model_lock:
            self.halted = False
            self.last_line = 0
            self.autoreport_interval = 0.0
            self.hotend.set_target(0)
            self.bed.set_target(0)
            self.homed = False
        self._boot()

    def _boot(self) -> None:
        def chatter() -> None:
            self._emit("start")
            self._emit(f"echo:{self.firmware_name}")
            self._emit("echo: Last Updated: 2026-01-01 | Author: (none, default config)")
            self._emit("echo: Compiled: Sep 14 2026")
            self._emit("echo: Free Memory: 3000  PlannerBufferBytes: 1152")
            self._emit("echo:V88 stored settings retrieved (630 bytes; crc 31459)")
            self._emit("echo:SD init fail")

        threading.Timer(self.boot_delay * self.time_scale, chatter).start()

    def _kill(self) -> None:
        self.halted = True
        self._emit("Error:Printer halted. kill() called!")

    def _emit(self, line: str) -> None:
        with self._out_cv:
            if self._closed or self._gone:
                return
            if self._swallow_ok and line.startswith("ok"):
                self._swallow_ok = False
                return
            self._out += (line + "\n").encode()
            self._out_cv.notify_all()

    def _sleep(self, seconds: float) -> None:
        time.sleep(seconds * self.time_scale)

    def _work(self, seconds: float) -> None:
        """Block for a while, sending host keepalives like Marlin does every 2 s."""
        remaining = seconds
        while remaining > 0:
            step = min(2.0, remaining)
            self._sleep(step)
            remaining -= step
            if remaining > 0:
                self._emit("echo:busy: processing")

    def temperature_report(self) -> str:
        with self._model_lock:
            hot = self.hotend.update()
            bed = self.bed.update()
            return (
                f" T:{hot:.2f} /{self.hotend.target:.2f} B:{bed:.2f} /{self.bed.target:.2f}"
                f" @:{127 if self.hotend.heating else 0} B@:{127 if self.bed.heating else 0}"
            )

    def _autoreport(self) -> None:
        while not self._closed:
            interval = self.autoreport_interval
            if interval <= 0:
                self._sleep(0.1)
                continue
            self._sleep(interval)
            if self.autoreport_interval > 0 and not self.halted:
                self._emit(self.temperature_report())

    # ---- command processing ------------------------------------------------------

    def _run(self) -> None:
        while True:
            line = self._commands.get()
            if line is None:
                return
            if self.halted:
                continue  # a killed firmware sits in an endless loop and answers nothing
            if self.latency:
                time.sleep(self.latency)
            self._process(line)

    def _process(self, line: str) -> None:
        match = _LINE_RE.match(line)
        if match:
            number = int(match.group("n"))
            body = f"N{number} {match.group('body')}"
            command = match.group("body").strip()
            given = match.group("cs")
            self.lines_received += 1
            if self.drop_every > 0 and self.lines_received % self.drop_every == 0 and number != self._last_dropped:
                self._last_dropped = number
                return  # lost on the wire: the printer never learns the line existed
            inject = (
                self.resend_every > 0
                and self.lines_received % self.resend_every == 0
                and number != self._last_injected
            )
            if given is None or int(given) != checksum(body) or inject:
                self._last_injected = number
                self._request_resend("checksum mismatch")
                return
            if not command.startswith("M110") and number != self.last_line + 1:
                self._request_resend("Line Number is not Last Line Number+1")
                return
            self.last_line = number
            if self.drop_ok_every > 0 and self.lines_received % self.drop_ok_every == 0:
                self._swallow_ok = True  # executed, but the host never sees the ok
        else:
            command = line.split("*", 1)[0].strip()

        command = command.split(";", 1)[0].strip()
        self.commands.append(command)
        self._command = command
        self._execute(command)

    def _request_resend(self, reason: str) -> None:
        self._emit(f"Error:{reason}, Last Line: {self.last_line}")
        self._emit(f"Resend: {self.last_line + 1}")
        self._emit("ok")

    def _execute(self, command: str) -> None:
        if not command:
            self._emit("ok")
            return
        params = self._params(command)
        code = command.split()[0].upper()
        handler = getattr(self, f"_cmd_{code}", None)
        if handler is not None:
            handler(params)
        elif code in _SILENT_OK:
            self._emit("ok")
        else:
            self._emit(f'echo:Unknown command: "{command}"')
            self._emit("ok")

    @staticmethod
    def _params(command: str) -> dict[str, float | None]:
        params: dict[str, float | None] = {}
        for match in _PARAM_RE.finditer(command.upper()):
            value = match.group("value")
            try:
                params[match.group("letter")] = float(value) if value not in ("", "-", ".") else None
            except ValueError:
                params[match.group("letter")] = None
        return params

    # G-codes

    def _move(self, params: dict) -> None:
        if params.get("F"):
            self.feedrate = params["F"]
        distance = 0.0
        with self._model_lock:
            for axis in ("X", "Y", "Z", "E"):
                value = params.get(axis)
                if value is None:
                    continue
                relative = self.relative or (axis == "E" and self.relative_e)
                target = self.position[axis] + value if relative else value
                distance = max(distance, abs(target - self.position[axis]))
                self.position[axis] = target
        seconds = min(2.0, distance / (self.feedrate / 60.0)) if self.feedrate else 0.0
        self._sleep(seconds)
        self._emit("ok")

    _cmd_G0 = _move
    _cmd_G1 = _move

    def _cmd_G4(self, params: dict) -> None:
        seconds = (params.get("S") or 0.0) + (params.get("P") or 0.0) / 1000.0
        self._work(seconds)
        self._emit("ok")

    def _cmd_G28(self, params: dict) -> None:
        self._work(3.0)
        with self._model_lock:
            self.position.update({"X": 0.0, "Y": 0.0, "Z": 0.0})
            self.homed = True
        self._emit(self._position_report())
        self._emit("ok")

    def _cmd_G29(self, params: dict) -> None:
        """Probes the grid point by point, reporting each one the way Marlin does at G29 V3."""
        with self._model_lock:
            self.mesh = [[_bed_height(x, y) for x in range(MESH_POINTS)] for y in range(MESH_POINTS)]
        for y, row in enumerate(self.mesh):
            for x, z in enumerate(row):
                self._work(0.5)
                self._emit(f"Bed X: {x * 50:.3f} Y: {y * 50:.3f} Z: {z:.3f}")
        self._report_mesh()
        self._emit("ok")

    def _cmd_M420(self, params: dict) -> None:
        if "V" in params and self.mesh:
            self._report_mesh()
        self._emit(f"echo:Bed Leveling {'ON' if self.mesh else 'OFF'}")
        self._emit("ok")

    def _report_mesh(self) -> None:
        """The grid as Marlin's print_2d_array writes it: column labels, then one row per Y."""
        self._emit("Bilinear Leveling Grid:")
        self._emit("".join(f"{x:>7}" for x in range(MESH_POINTS)))
        for y, row in enumerate(self.mesh):
            self._emit(f"{y:>2}" + "".join(f" {z:+.3f}" for z in row))

    def _cmd_G90(self, params: dict) -> None:
        self.relative = False
        self._emit("ok")

    def _cmd_M82(self, params: dict) -> None:
        self.relative_e = False
        self._emit("ok")

    def _cmd_M83(self, params: dict) -> None:
        self.relative_e = True
        self._emit("ok")

    def _cmd_G91(self, params: dict) -> None:
        self.relative = True
        self._emit("ok")

    def _cmd_G92(self, params: dict) -> None:
        with self._model_lock:
            for axis in ("X", "Y", "Z", "E"):
                if params.get(axis) is not None:
                    self.position[axis] = params[axis]
        self._emit("ok")

    # M-codes

    def _cmd_M104(self, params: dict) -> None:
        with self._model_lock:
            self.hotend.set_target(params.get("S") or 0.0)
        self._emit("ok")

    def _cmd_M140(self, params: dict) -> None:
        with self._model_lock:
            self.bed.set_target(params.get("S") or 0.0)
        self._emit("ok")

    def _cmd_M105(self, params: dict) -> None:
        self._emit("ok" + self.temperature_report())

    def _wait_for(self, heater: _Heater, params: dict) -> None:
        target = params.get("S") if params.get("S") is not None else params.get("R")
        with self._model_lock:
            heater.set_target(target or 0.0)
        if not target:
            self._emit("ok")
            return
        self._break_wait = False
        for _ in range(600):
            with self._model_lock:
                done = heater.at_target()
            if done or self._break_wait:
                break
            self._sleep(1.0)
            self._emit(self.temperature_report() + " W:?")
        self._emit("ok")

    def _cmd_M109(self, params: dict) -> None:
        self._wait_for(self.hotend, params)

    def _cmd_M190(self, params: dict) -> None:
        self._wait_for(self.bed, params)

    def _cmd_M110(self, params: dict) -> None:
        if params.get("N") is not None:
            self.last_line = int(params["N"])
        self._emit("ok")

    def _cmd_M114(self, params: dict) -> None:
        self._emit(self._position_report())
        self._emit("ok")

    def host_action(self, name: str) -> None:
        """Send a host action command the way the firmware does, e.g. a pause from the screen."""
        self._emit(f"// action:{name}" if self.firmware != "prusa" else f"//action:{name}")

    def _cmd_M601(self, params: dict) -> None:
        if self.firmware is None:
            self._emit('echo:Unknown command: "M601"')
            self._emit("ok")
            return
        self.paused = True
        self._emit("ok")
        self._sleep(self.pause_delay)
        # Buddy acknowledges at once, parks in the background and then tells the host; the MK3
        # acknowledges, parks and reports that it has paused.
        self.host_action("pause" if self.firmware == "buddy" else "paused")

    def _cmd_M602(self, params: dict) -> None:
        if self.firmware is None:
            self._emit('echo:Unknown command: "M602"')
            self._emit("ok")
            return
        if not self.paused:
            self._emit("ok")
            return
        self.paused = False
        if self.firmware == "buddy":
            # Buddy acknowledges, reheats and returns, and only then accepts G-code again.
            self._emit("ok")
            if self.resume_delay is not None:
                self._sleep(self.resume_delay)
                self.host_action("resume")
        else:
            # The MK3 reheats and returns first and acknowledges afterwards.
            self._sleep(self.resume_delay or 0.0)
            self.host_action("resumed")
            self._emit("ok")

    def _cmd_M115(self, params: dict) -> None:
        self._emit(
            f"FIRMWARE_NAME:{self.firmware_name} SOURCE_CODE_URL:github.com/MarlinFirmware/Marlin"
            " PROTOCOL_VERSION:1.0 MACHINE_TYPE:PrintPi Fake EXTRUDER_COUNT:1"
            " UUID:cede2a2f-41a2-4748-9b12-c55c62f367ff"
        )
        for name, value in (
            ("SERIAL_XON_XOFF", 0),
            ("EEPROM", 1),
            ("AUTOREPORT_TEMP", 1),
            ("AUTOREPORT_POS", 0),
            ("PROGRESS", 0),
            ("EMERGENCY_PARSER", 1),
            ("HOST_ACTION_COMMANDS", 0),
            ("SDCARD", 1),
        ):
            self._emit(f"Cap:{name}:{value}")
        self._emit("ok")

    def _cmd_M155(self, params: dict) -> None:
        self.autoreport_interval = float(params.get("S") or 0.0)
        self._emit("ok")

    def _cmd_M20(self, params: dict) -> None:
        self._emit("Begin file list")
        for name, size in DRIVE_FILES:
            self._emit(f"{name} {size}")
        self._emit("End file list")
        self._emit("ok")

    def _cmd_M997(self, params: dict) -> None:
        """Firmware update the Buddy way: reboot, and flash the named file from the drive on the way.

        The ok goes out first like on the real board, then the device disappears; a
        plain M997 is the restart 32-bit Marlin boards do to pick up firmware.bin.
        """
        match = re.search(r"/usb/(\S+)", self._command, re.IGNORECASE)
        if match and match.group(1).upper() in {name for name, _ in DRIVE_FILES}:
            FakePrinter.next_firmware_name = FLASHED_FIRMWARE_NAME
        self._emit("ok")
        with self._out_cv:
            self._gone = True
            self._out_cv.notify_all()

    def _cmd_M21(self, params: dict) -> None:
        self._emit("echo:SD init fail")
        self._emit("ok")

    def _cmd_M503(self, params: dict) -> None:
        self._emit("echo:  G21    ; Units in mm (mm)")
        self._emit("echo:  M92 X80.00 Y80.00 Z400.00 E93.00")
        self._emit("ok")

    def _position_report(self) -> str:
        with self._model_lock:
            p = self.position
            return (
                f"X:{p['X']:.2f} Y:{p['Y']:.2f} Z:{p['Z']:.2f} E:{p['E']:.2f}"
                f" Count X:{int(p['X'] * 80)} Y:{int(p['Y'] * 80)} Z:{int(p['Z'] * 400)}"
            )


# Commands the fake accepts with a plain "ok" and no side effects.
_SILENT_OK = {
    "G21", "G20", "M17", "M18", "M84", "M106", "M107", "M117", "M118",
    "M220", "M221", "M300", "M400", "M500", "M501", "M502", "M600", "M851",
    "M900", "M301", "M304", "M204", "M205", "M203", "M201", "M92", "M211", "M413",
    "M75", "M76", "M77", "M73", "M31", "M24", "M25", "M26", "M27", "M23", "M22", "T0",
    "M108", "M591", "M865",
}
