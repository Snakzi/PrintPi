"""Printer connection: owns the serial port and drives the Marlin protocol.

One command is in flight at a time. send() writes a numbered, checksummed line and
blocks until the firmware answers "ok". A reader thread turns incoming lines into
state updates, extends the timeout while the firmware reports "busy", and handles
"Resend" by writing the requested line again from a short history.

A line can get lost on the way to the printer (seen on the MK4S over USB); the
firmware then never answers and never asks for a resend, because it does not know
the line existed. After `probe_timeout` without any sign of progress send() writes
an M105 with the next line number: a printer that missed the line rejects the probe
and asks for a resend of the lost one, a printer that is merely slow answers both.
The probe has to come quickly, since Prusa's Buddy firmware ends a serial print on
its own once its queue has been empty for five seconds.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict, deque
from typing import Callable

from . import protocol
from .serial_log import SerialLog
from .state import PrinterState, Temperature
from .transport import open_port

log = logging.getLogger("printpi.printer")

StateListener = Callable[[PrinterState], None]
LineListener = Callable[[str, str], None]  # direction ("tx" | "rx"), line
ActionListener = Callable[[str], None]  # a host action command the printer sent (pause, resume, cancel)


class PrinterError(Exception):
    pass


class NotConnected(PrinterError):
    pass


class CommandTimeout(PrinterError):
    pass


class PrinterHalted(PrinterError):
    pass


RESEND_OK = -1  # placeholder in the ack queue for the ok that follows a Resend request
PROBE_COMMAND = "M105"
MAX_PROBES = 2  # per command


class Printer:
    def __init__(
        self,
        port_url: str,
        baudrate: int = 115200,
        *,
        serial_log: SerialLog | None = None,
        on_state: StateListener | None = None,
        on_line: LineListener | None = None,
        on_action: ActionListener | None = None,
        temperature_interval: float = 2.0,
        ok_timeout: float = 30.0,
        probe_timeout: float | None = 3.0,
        connect_timeout: float = 5.0,
    ) -> None:
        self.port_url = port_url
        self.baudrate = baudrate
        self.serial_log = serial_log or SerialLog(None)
        self.on_state = on_state
        self.on_line = on_line
        self.on_action = on_action
        self.temperature_interval = temperature_interval
        self.ok_timeout = ok_timeout
        self.probe_timeout = probe_timeout
        self.connect_timeout = connect_timeout

        self.state = PrinterState(port=port_url, baudrate=baudrate)
        self._state_lock = threading.RLock()
        self._port = None
        self._reader_thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._start_seen = threading.Event()

        self._send_lock = threading.Lock()  # one command in flight
        self._ack = threading.Event()
        self._response_lines: list[str] = []
        self._deadline = 0.0
        self._progress_at = 0.0  # when the printer last acknowledged, asked for a resend or reported busy
        # Line numbers whose "ok" is still to come, in wire order; RESEND_OK stands for the ok
        # Marlin sends right after a "Resend" request. The reader pops one entry per ok.
        self._expect: deque[int] = deque()
        self._expect_lock = threading.Lock()  # the reader pops while the sender appends
        self._resend_line: int | None = None
        self._failure: PrinterError | None = None
        self._line_number = 0
        self._sent_lines: OrderedDict[int, str] = OrderedDict()
        self._history_size = 64

    # ---- connection lifecycle -------------------------------------------------

    @property
    def connected(self) -> bool:
        return self._port is not None and self.state.connection == "connected"

    @property
    def firmware_family(self) -> str:
        """"buddy" for Prusa's 32-bit printers, "prusa" for the MK3 family, else "marlin"."""
        name = self.state.firmware.get("FIRMWARE_NAME", "")
        if "Buddy" in name:
            return "buddy"
        if name.startswith("Prusa-Firmware"):
            return "prusa"
        return "marlin"

    def connect(self) -> None:
        if self._port is not None:
            raise PrinterError("already connected")
        self._stop.clear()
        self._start_seen.clear()
        self._failure = None
        self._update(connection="connecting", status="idle", last_error=None,
                     firmware={}, capabilities={}, temperatures={}, position={})
        try:
            self._port = open_port(self.port_url, self.baudrate, timeout=0.5)
        except Exception as exc:
            self._update(connection="error", last_error=f"could not open {self.port_url}: {exc}")
            raise PrinterError(f"could not open {self.port_url}: {exc}") from exc
        self.serial_log.event(f"opened {self.port_url} at {self.baudrate} baud")
        self._reader_thread = threading.Thread(target=self._reader, name="printer-reader", daemon=True)
        self._reader_thread.start()
        try:
            self._handshake()
        except PrinterError as exc:
            self.disconnect(error=f"handshake failed: {exc}")
            raise
        self._update(connection="connected", status="idle")
        if not self.state.capabilities.get("AUTOREPORT_TEMP"):
            threading.Thread(target=self._poll_temperatures, name="printer-temps", daemon=True).start()

    def _handshake(self) -> None:
        # Opening a USB port resets most boards through DTR and they print "start".
        # Over a TCP bridge nothing resets, so don't insist on seeing it.
        if self._start_seen.wait(self.connect_timeout):
            self.serial_log.event("printer reported start")
            time.sleep(0.3)  # let the boot chatter finish before we talk
        else:
            self.serial_log.event("no start received, assuming the printer is already running")
        self._line_number = 0
        self._sent_lines.clear()
        self._expect.clear()
        self.send("M110 N0", timeout=self.connect_timeout)
        self.send("M115", timeout=self.connect_timeout)
        if self.state.capabilities.get("AUTOREPORT_TEMP"):
            self.send(f"M155 S{max(1, int(self.temperature_interval))}", timeout=self.connect_timeout)
        self.send("M105", timeout=self.connect_timeout)

    def disconnect(self, error: str | None = None) -> None:
        self._stop.set()
        port, self._port = self._port, None
        if port is not None:
            try:
                port.close()
            except Exception:  # noqa: BLE001 - closing is best effort
                pass
            self.serial_log.event(f"closed {self.port_url}" + (f": {error}" if error else ""))
        self._fail(NotConnected(error or "disconnected"))
        thread = self._reader_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2)
        self._update(connection="error" if error else "offline", status="idle", last_error=error)

    # ---- sending ------------------------------------------------------------------

    def send(self, command: str, *, timeout: float | None = None) -> list[str]:
        """Send one G-code command and block until the firmware acknowledges it.

        Returns the lines received between sending and the "ok" (echo, errors,
        position reports); temperature reports update the state instead.
        """
        command = protocol.strip_comment(command)
        if not command:
            return []
        if self._port is None:
            raise NotConnected("not connected")
        with self._send_lock:
            if self.state.status == "halted":
                raise PrinterHalted(self.state.last_error or "printer halted")
            if self._failure is not None:
                raise self._failure
            number = self._line_number
            line = protocol.format_line(command, number)
            self._ack.clear()
            self._response_lines = []
            self._resend_line = None
            self._remember(number, line)
            self._line_number = number + 1
            # A running print job holds the status at "printing"; only an idle
            # printer flips to "busy" for the duration of a single command.
            was_idle = self.state.status == "idle"
            if was_idle:
                self._set_status("busy")
            try:
                self._write(line)
                self._deadline = time.monotonic() + (timeout or self.ok_timeout)
                self._wait_for_ack(number, line)
            finally:
                if was_idle and self.state.status == "busy":
                    self._set_status("idle")
            return list(self._response_lines)

    def set_status(self, status: str) -> None:
        """Hold the status at "printing" or "paused" while a job runs, "idle" afterwards."""
        self._set_status(status)

    def emergency_stop(self) -> None:
        """M112 bypasses the queue: written immediately, no ok expected."""
        if self._port is None:
            raise NotConnected("not connected")
        self._write("M112")
        self._update(status="halted", last_error="emergency stop sent")
        self._fail(PrinterHalted("emergency stop sent"))

    def interrupt_wait(self) -> None:
        """M108 makes a firmware with an emergency parser abandon a heat-up (M109/M190) early.

        Written raw like M112, so it reaches the parser while a command is in flight.
        """
        if self._port is None:
            raise NotConnected("not connected")
        if not self.state.capabilities.get("EMERGENCY_PARSER"):
            return
        self._write("M108")

    def _wait_for_ack(self, number: int, line: str) -> None:
        probes = 0
        while True:
            now = time.monotonic()
            remaining = self._deadline - now
            if remaining <= 0:
                self.disconnect(error=f"no ok within timeout for {line!r}")
                raise CommandTimeout(f"no ok within timeout for {line!r}")
            # Recomputed every turn: a busy keepalive or a heating report moves it out again.
            probe_at = self._next_probe_time(probes)
            if probe_at is not None and now >= probe_at:
                self._probe(line)
                probes += 1
                continue
            wait = min(remaining, 0.25) if probe_at is None else min(remaining, max(probe_at - now, 0.01), 0.25)
            if not self._ack.wait(wait):
                continue
            self._ack.clear()
            if self._failure is not None:
                raise self._failure
            if self._resend_line is not None:
                requested, self._resend_line = self._resend_line, None
                self._resend_from(requested)
                probes = 0
            with self._expect_lock:
                if number not in self._expect:
                    return

    def _next_probe_time(self, probes: int) -> float | None:
        """When to probe next: after `probe_timeout` of silence, once more after three times that,
        then never for this command. A firmware that blocks for a minute without keepalives must
        not have its input buffer filled with probes it cannot read, which blocks the write."""
        if self.probe_timeout is None or probes >= MAX_PROBES:
            return None
        return self._progress_at + self.probe_timeout * (3 if probes else 1)

    def _probe(self, line: str) -> None:
        """Ask for temperatures with the next line number, so a lost line shows up as a Resend."""
        number = self._line_number
        probe = protocol.format_line(PROBE_COMMAND, number)
        self.serial_log.event(f"no answer to {line!r} for {self.probe_timeout:g} s, probing with {probe!r}")
        log.warning("no answer to %r for %g s, probing the printer", line, self.probe_timeout)
        self._remember(number, probe)
        self._line_number = number + 1
        self._progress_at = time.monotonic()
        self._write(probe)

    def _resend_from(self, number: int) -> None:
        lines = [(n, l) for n, l in self._sent_lines.items() if n >= number]
        known = lines[0][0] == number if lines else number == self._line_number
        if not known:
            self.disconnect(error=f"printer asked for resend of line {number}, which is not in history")
            raise self._failure  # type: ignore[misc]
        if lines:
            self.serial_log.event(f"resending from line {number}")
        for n, line in lines:
            with self._expect_lock:
                self._expect.append(n)
            self._write(line)
        self._deadline = time.monotonic() + self.ok_timeout

    def _remember(self, number: int, line: str) -> None:
        self._sent_lines[number] = line
        with self._expect_lock:
            self._expect.append(number)
        while len(self._sent_lines) > self._history_size:
            self._sent_lines.popitem(last=False)

    def _write(self, line: str) -> None:
        port = self._port
        if port is None:
            raise NotConnected("not connected")
        self.serial_log.tx(line)
        self._notify_line("tx", line)
        self._progress_at = time.monotonic()
        try:
            port.write((line + "\n").encode("ascii", "replace"))
        except Exception as exc:
            self.disconnect(error=f"write failed: {exc}")
            raise NotConnected(f"write failed: {exc}") from exc

    def _acknowledge(self, with_temperatures: bool) -> None:
        """One ok arrived: drop the entry it belongs to.

        An ok carrying temperatures is the reply to an M105, so it settles everything up to
        the first pending M105, which covers an earlier ok the host never saw.
        """
        with self._expect_lock:
            if with_temperatures:
                for index, number in enumerate(self._expect):
                    if number != RESEND_OK and self._is_temperature_query(number):
                        for _ in range(index + 1):
                            self._expect.popleft()
                        return
            if self._expect:
                self._expect.popleft()

    def _is_temperature_query(self, number: int) -> bool:
        command = self._sent_lines.get(number, "").split(" ", 1)[1:]
        return bool(command) and command[0].upper().startswith(PROBE_COMMAND)

    def _fail(self, error: PrinterError) -> None:
        if self._failure is None:
            self._failure = error
        self._ack.set()

    # ---- receiving ----------------------------------------------------------------

    def _reader(self) -> None:
        port = self._port
        buffer = bytearray()
        while not self._stop.is_set() and port is not None:
            try:
                data = port.read(max(1, getattr(port, "in_waiting", 0)))
            except Exception as exc:  # noqa: BLE001 - any read failure ends the connection
                if not self._stop.is_set():
                    self.disconnect(error=f"read failed: {exc}")
                return
            if not data:
                continue
            buffer += data
            while (index := buffer.find(b"\n")) >= 0:
                raw = bytes(buffer[:index])
                del buffer[: index + 1]
                line = raw.decode("utf-8", errors="replace").rstrip("\r")
                self.serial_log.rx(line)
                self._notify_line("rx", line)
                self._handle(protocol.parse(line))

    def _handle(self, msg: protocol.Message) -> None:
        kind = msg.kind
        if kind == "empty":
            return
        if kind == "start":
            if self.state.connection == "connected":
                # The board rebooted underneath us (brown-out, watchdog). Line
                # numbers are gone; the safe thing is to drop the connection.
                self.disconnect(error="printer reset while connected")
                return
            self._start_seen.set()
            return
        if msg.temperatures:
            self._update_temperatures(msg.temperatures)
        if kind == "ok":
            self._progress_at = time.monotonic()
            self._acknowledge(bool(msg.temperatures))
            self._ack.set()
            return
        if kind == "resend" and msg.resend_line is not None:
            self._progress_at = time.monotonic()
            # The printer flushed its input: lines from the requested one on never get an
            # ok, earlier ones still do, and Marlin sends one ok for the request itself.
            with self._expect_lock:
                while self._expect and self._expect[-1] != RESEND_OK and self._expect[-1] >= msg.resend_line:
                    self._expect.pop()
                self._expect.append(RESEND_OK)
            self._resend_line = msg.resend_line
            self._ack.set()
            return
        if kind == "busy":
            self._deadline = time.monotonic() + self.ok_timeout
            self._progress_at = time.monotonic()
            return
        if kind == "temperature":
            # Heating reports ("T:... W:?") are the only sign of life some firmwares
            # give during M109/M190, which can run for minutes.
            if msg.waiting:
                self._deadline = time.monotonic() + self.ok_timeout
                self._progress_at = time.monotonic()
            return
        if kind == "action" and msg.action:
            self.serial_log.event(f"printer action: {msg.action}")
            listener = self.on_action
            if listener is not None:
                try:
                    listener(msg.action)
                except Exception:  # noqa: BLE001 - a listener must not take the reader down
                    log.exception("action listener failed")
            return
        if kind == "position":
            self._update(position=msg.position)
        elif kind == "firmware":
            self._update(firmware=msg.firmware)
        elif kind == "capability" and msg.capability:
            with self._state_lock:
                self.state.capabilities[msg.capability[0]] = msg.capability[1]
        elif kind == "error":
            self._update(last_error=msg.error)
            if msg.error and ("halted" in msg.error.lower() or "kill()" in msg.error or msg.raw.startswith("!!")):
                self._update(status="halted")
                self._fail(PrinterHalted(msg.error))
        self._response_lines.append(msg.raw.strip())

    def _poll_temperatures(self) -> None:
        while not self._stop.wait(self.temperature_interval):
            if self._port is None or self.state.status == "halted":
                return
            if self._send_lock.locked():
                continue  # a long command is running; M109 and friends report on their own
            try:
                self.send("M105")
            except PrinterError:
                return

    # ---- state ----------------------------------------------------------------------

    def _update_temperatures(self, readings: dict[str, tuple[float, float | None]]) -> None:
        with self._state_lock:
            for sensor, (actual, target) in readings.items():
                self.state.temperatures[sensor] = Temperature(actual=actual, target=target)
        self._update()

    def _set_status(self, status: str) -> None:
        self._update(status=status)

    def _update(self, **fields) -> None:
        with self._state_lock:
            for key, value in fields.items():
                setattr(self.state, key, value)
            self.state.updated_at = time.time()
            snapshot = self.state.snapshot() if self.on_state else None
        if snapshot is not None:
            try:
                self.on_state(snapshot)  # type: ignore[misc]
            except Exception:  # noqa: BLE001 - listeners must never break the reader
                log.exception("state listener failed")

    def _notify_line(self, direction: str, line: str) -> None:
        if self.on_line is None:
            return
        try:
            self.on_line(direction, line)
        except Exception:  # noqa: BLE001
            log.exception("line listener failed")
