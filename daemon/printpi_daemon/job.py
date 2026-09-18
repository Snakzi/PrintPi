"""Print jobs: stream a G-code file to the printer with pause, resume and cancel.

JobBackend is the small interface the bridge drives. SerialJobRunner is the only
implementation today and feeds the file through Printer.send(); a PrusaLink or
Moonraker backend would implement the same methods and report the same JobState.

The runner works on its own thread so the bridge stays responsive to pause and
cancel. Comments and blank lines are skipped but counted, so `line` is always a
line number of the file as uploaded and the live preview can map it back to the
parsed moves. Progress comes from the M73 P<percent> lines PrusaSlicer and
OrcaSlicer write, else it is measured in bytes of commands; comments are left out
because the thumbnails and the config block a slicer embeds would otherwise jump
the bar by a quarter before the first move. The remaining time comes from the M73
R<minutes> lines, else from the slicer's estimate blended with the pace so far.
Until the first layer marker the job reports what the start G-code is doing as
`activity` (heating, homing, levelling, purging) and holds the remaining time,
since the slicer's clock does not cover heating; after that the M73 figure is
scaled by how much slower or faster than the slicer the printer has been.

A pause has to get the nozzle off the part and, on Prusa printers, has to be the
firmware's own pause: Buddy ends a serial print by itself once its queue has been
empty for five seconds, unless it is in its paused state. So on Prusa firmware the
runner sends M601 and M602 and lets the printer park, cool, reheat and return, the
way a host is expected to on those printers; on other Marlin
firmware it runs a small script of its own that records the position, retracts,
lifts and parks, and puts everything back on resume. The printer's host action
commands ("// action:pause", "resume", "cancel") drive the job the same way, so a
pause at the printer's screen or an M601 in the file pauses the stream too.

The runner also knows when the part itself is done: the pre-scan finds the last
extruding move, and before the first travel after it (the end G-code's park) the
runner waits for the moves to finish and calls `on_part_finished`, which is when
the timelapse takes its closing frame with the part still in view.
"""

from __future__ import annotations

import copy
import logging
import os
import re
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Callable

from . import protocol
from .printer import Printer, PrinterError

log = logging.getLogger("printpi.job")

# After a cancel: fans and heaters off, nozzle lifted off the part, motors released.
DEFAULT_CANCEL_GCODE = ["M107", "M104 S0", "M140 S0", "G91", "G1 Z10 F600", "G90", "M84"]
# Firmware families whose M601/M602 park and return by themselves and report host actions.
PRUSA_FAMILIES = ("buddy", "prusa")
# The runner's own pause on other firmware: retract, lift, park in the back left corner.
PAUSE_RETRACT_MM = 2.0
PAUSE_LIFT_MM = 5.0
PAUSE_PARK_INSET_MM = 5.0
# M602 blocks on the MK3 until the print is back in position, and Buddy reports "action:resume"
# only after reheating; either can take minutes.
RESUME_TIMEOUT = 600.0

ACTIVE_STATES = ("printing", "paused", "cancelling")

_M73_PERCENT_RE = re.compile(r"^M73\b.*?\bP(\d+(?:\.\d+)?)", re.IGNORECASE)
_M73_REMAINING_RE = re.compile(r"^M73\b.*?\bR(\d+(?:\.\d+)?)", re.IGNORECASE)
_LAYER_MARKER_RE = re.compile(rb"^;[ \t]*LAYER(?:_CHANGE|:)", re.MULTILINE)
_HEATING_CODES = ("M109", "M190", "M191", "M116")
_LEVELING_CODES = ("G29", "G80", "M420")
# The slicer's remaining time is trusted once it has seen this much of the print, and its
# pace is corrected within these bounds; a printer twice as slow as the slicer is rare.
_PACE_AFTER = 120.0
_PACE_RANGE = (0.5, 2.5)
# Blank and comment-only lines, which the runner skips without sending.
_SKIPPED_LINE_RE = re.compile(rb"^[ \t]*(?:;[^\n]*)?\r?\n", re.MULTILINE)
_LAYER_MARKER_PREFIXES = (b";LAYER_CHANGE", b";LAYER:", b"; LAYER_CHANGE", b"; LAYER:")
_SCAN_CHUNK = 1 << 20
_FEEDRATE_RE = re.compile(r"\bF(\d+(?:\.\d+)?)", re.IGNORECASE)
# A move that pushes filament: G0/G1 with a positive E word.
_EXTRUSION_LINE_RE = re.compile(rb"^[ \t]*G[01]\b[^\n;]*?[ \t]E(\d*\.?\d+)", re.MULTILINE | re.IGNORECASE)
_TAIL_WINDOW = 1 << 18

JobListener = Callable[["JobState"], None]


class JobError(Exception):
    pass


@dataclass
class JobState:
    name: str
    path: str
    file_id: int | None = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])  # names the history record of this run
    state: str = "printing"  # printing | paused | cancelling | finished | cancelled | error
    error: str | None = None
    progress: float = 0.0  # 0..1 from M73 P, else by command bytes
    line: int = 0  # lines of the file handed to the printer or skipped so far
    total_lines: int | None = None
    bytes_sent: int = 0  # bytes of command lines handed to the printer
    total_bytes: int = 0  # bytes of command lines in the file, known after the pre-scan
    layer: int = 0  # 1-based, counted from ;LAYER_CHANGE or ;LAYER: markers
    total_layers: int | None = None
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    elapsed: float = 0.0  # seconds spent printing, pauses excluded
    remaining: float | None = None
    remaining_source: str | None = None  # m73 | slicer | progress
    estimated_seconds: int | None = None
    energy_wh: float | None = None  # metered by the bridge when a plugin reports the printer's power draw
    # preparing | heating | homing | cleaning | leveling | purging | loading, None once the first layer runs;
    # pausing and resuming while the pause or resume script runs
    activity: str | None = "preparing"

    @property
    def active(self) -> bool:
        return self.state in ACTIVE_STATES

    def to_dict(self) -> dict:
        return asdict(self)


class JobBackend:
    """What the bridge needs from a job backend, whatever talks to the printer."""

    @property
    def state(self) -> JobState | None:
        raise NotImplementedError

    def start(self, path: str, *, name: str | None = None, file_id: int | None = None,
              estimated_seconds: int | None = None, bed: dict | None = None,
              cancel_gcode: list[str] | None = None) -> JobState:
        """bed is the profile's {"x", "y", "z", "centered"}, for the park position of a pause;
        cancel_gcode replaces the built-in script run after a cancel."""
        raise NotImplementedError

    def pause(self) -> None:
        raise NotImplementedError

    def handle_action(self, action: str) -> None:
        """A host action command from the printer: pause, paused, resume, resumed or cancel."""

    def resume(self) -> None:
        raise NotImplementedError

    def cancel(self) -> None:
        raise NotImplementedError

    def restart(self) -> JobState:
        """Print the last job again."""
        raise NotImplementedError

    def stop(self) -> None:
        """Daemon shutdown: end the job without talking to the printer."""

    def add_energy(self, watt_hours: float) -> None:
        """Account energy the printer drew while this job was active."""


def activity_of(command: str) -> str | None:
    """What the printer is busy with for a command of the start G-code, None for the many that are instant."""
    words = command.upper().split()
    if not words:
        return None
    code = words[0]
    if code in _HEATING_CODES:
        return "heating"
    if code == "G28":
        return "homing"
    if code == "G29":
        return "cleaning" if "P9" in words[1:] else "leveling"  # Prusa's G29 P9 wipes the nozzle
    if code in _LEVELING_CODES:
        return "leveling"
    if code == "M701":
        return "loading"
    if code in ("G0", "G1"):
        extrudes = any(word.startswith("E") and _positive(word[1:]) for word in words[1:])
        moves = any(word[0] in "XY" for word in words[1:])
        if extrudes and moves:
            return "purging"
    return None


def _positive(text: str) -> bool:
    try:
        return float(text) > 0
    except ValueError:
        return False


def pace_factor(actual: float, expected: float | None) -> float:
    """How much longer the printer takes than the slicer expected, once enough of the print has run to tell."""
    if expected is None or expected < _PACE_AFTER or actual <= 0:
        return 1.0
    return min(_PACE_RANGE[1], max(_PACE_RANGE[0], actual / expected))


def scan_file(path: str) -> tuple[int, int, int]:
    """Count the lines, the layer markers and the bytes of command lines the way the runner will see them."""
    lines = layers = command_bytes = 0
    with open(path, "rb") as handle:
        rest = b""
        while chunk := handle.read(_SCAN_CHUNK):
            data = rest + chunk
            # Work on whole lines only; the partial last line waits for the next chunk.
            cut = data.rfind(b"\n") + 1
            complete, rest = data[:cut], data[cut:]
            lines += complete.count(b"\n")
            layers += len(_LAYER_MARKER_RE.findall(complete))
            command_bytes += len(complete) - sum(len(match.group(0)) for match in _SKIPPED_LINE_RE.finditer(complete))
    if rest:
        lines += 1
        layers += len(_LAYER_MARKER_RE.findall(rest))
        if not _SKIPPED_LINE_RE.match(rest + b"\n"):
            command_bytes += len(rest)
    return lines, layers, command_bytes


def last_extrusion_line(path: str, total_lines: int) -> int | None:
    """The 1-based line of the last move that extrudes, searched from the end of the file."""
    size = os.path.getsize(path)
    window = _TAIL_WINDOW
    with open(path, "rb") as handle:
        while True:
            start = max(0, size - window)
            handle.seek(start)
            data = handle.read(size - start)
            if start > 0:
                cut = data.find(b"\n") + 1  # the first line may be cut in two
                data, start = data[cut:], start + cut
            matches = [match for match in _EXTRUSION_LINE_RE.finditer(data) if float(match.group(1)) > 0]
            if matches:
                after = data.count(b"\n", matches[-1].start())
                return total_lines - after + (1 if data.endswith(b"\n") else 0)
            if start == 0:
                return None
            window *= 4


def leaves_the_part(command: str) -> bool:
    """A move that takes the nozzle away from the part after the last extrusion: a travel, a park,
    homing. A wipe (an XY move that retracts) still runs over the part and does not count."""
    words = command.upper().split()
    if not words:
        return False
    code = words[0]
    if code in ("G28", "G27"):
        return True
    if code not in ("G0", "G1"):
        return False
    moves = any(word[0] in "XY" for word in words[1:])
    retracts = any(word.startswith("E-") for word in words[1:])
    return moves and not retracts


class SerialJobRunner(JobBackend):
    """Streams a file through Printer.send() on a background thread."""

    def __init__(
        self,
        printer_provider: Callable[[], Printer],
        *,
        on_state: JobListener | None = None,
        on_part_finished: JobListener | None = None,
        cancel_gcode: list[str] | None = None,
        publish_interval: float = 0.5,
    ) -> None:
        self._printer_of = printer_provider
        self.on_state = on_state
        self.on_part_finished = on_part_finished
        self.cancel_gcode = list(cancel_gcode if cancel_gcode is not None else DEFAULT_CANCEL_GCODE)
        self.publish_interval = publish_interval

        self._lock = threading.RLock()
        self._cv = threading.Condition(self._lock)
        self._job: JobState | None = None
        self._printer: Printer | None = None
        self._thread: threading.Thread | None = None
        self._paused = False
        self._cancelled = False
        self._bed: dict | None = None
        self._printer_paused = False  # the printer paused by itself (action:paused), no M601 needed
        self._printer_resumed = False  # the printer resumed by itself (Buddy's action:resume)
        self._resumed = threading.Event()  # set by action:resume / action:resumed
        self._pause_position: dict[str, float] | None = None
        self._relative_positioning = False  # G91 seen in the file
        self._relative_extrusion = False  # M83 seen in the file
        self._feedrate: float | None = None  # the last F of a move in the file
        self._last_extrusion: int | None = None  # line of the last extruding move
        self._part_finished = False
        self._started = 0.0  # monotonic clock, for durations
        self._finished: float | None = None
        self._paused_total = 0.0
        self._pause_began: float | None = None
        # The slicer's remaining seconds, our elapsed when the line was sent, and what the slicer
        # thinks had elapsed by then (from M73 P), for the pace correction.
        self._m73: tuple[float, float, float | None] | None = None
        self._m73_progress: float | None = None  # 0..1 from the last M73 P
        self._print_started_at: float | None = None  # elapsed when the first layer began
        self._last_publish = 0.0
        self._last_temperature = 0.0

    # ---- JobBackend ------------------------------------------------------------------

    @property
    def state(self) -> JobState | None:
        with self._lock:
            if self._job is None:
                return None
            self._refresh_times(self._job)
            return copy.copy(self._job)

    def start(self, path: str, *, name: str | None = None, file_id: int | None = None,
              estimated_seconds: int | None = None, bed: dict | None = None,
              cancel_gcode: list[str] | None = None) -> JobState:
        with self._lock:
            if self._job is not None and self._job.active:
                raise JobError("a print is already running")
            printer = self._printer_of()
            if not printer.connected:
                raise JobError("printer is not connected")
            if not os.path.isfile(path):
                raise JobError(f"{path} does not exist")
            job = JobState(
                name=name or os.path.basename(path),
                path=path,
                file_id=file_id,
                estimated_seconds=estimated_seconds,
            )
            self._job = job
            self._printer = printer
            self._bed = dict(bed) if bed else self._bed
            self._job_cancel_gcode = [line for line in (cancel_gcode or []) if line.strip()] or None
            self._paused = self._cancelled = False
            self._printer_paused = self._printer_resumed = False
            self._resumed.clear()
            self._pause_position = None
            self._relative_positioning = self._relative_extrusion = False
            self._feedrate = None
            self._last_extrusion = None
            self._part_finished = False
            self._started = time.monotonic()
            self._finished = None
            self._paused_total = 0.0
            self._pause_began = None
            self._m73 = None
            self._m73_progress = None
            self._print_started_at = None
            self._last_publish = 0.0
            self._last_temperature = time.monotonic()
            printer.set_status("printing")
            self._thread = threading.Thread(target=self._run, args=(job, printer), name="print-job", daemon=True)
            self._thread.start()
            self._publish(job, force=True)
            log.info("printing %s (%d bytes)", job.name, os.path.getsize(path))
            return copy.copy(job)

    def pause(self) -> None:
        with self._cv:
            job = self._job
            if job is None or job.state != "printing":
                raise JobError("no print is running")
            self._paused = True
            self._cv.notify_all()

    def resume(self) -> None:
        with self._cv:
            job = self._job
            if job is None or job.state != "paused":
                raise JobError("the print is not paused")
            self._paused = False
            self._cv.notify_all()

    def handle_action(self, action: str) -> None:
        with self._cv:
            job = self._job
            if job is None or not job.active:
                return
            if action == "pause":
                # The MK3's screen asks the host to pause; Buddy says this once it has paused itself.
                if job.state == "printing" and not self._paused:
                    log.info("the printer asked to pause")
                    self._paused = True
            elif action == "paused":
                # The printer parked by itself, after our M601 or one in the file.
                self._printer_paused = True
                if job.state == "printing" and not self._paused:
                    log.info("the printer paused the print")
                    self._paused = True
            elif action in ("resume", "resumed"):
                self._resumed.set()
                if job.state == "paused" and self._paused:
                    log.info("the printer asked to resume")
                    printer = self._printer
                    self._printer_resumed = action == "resumed" or (printer is not None and printer.firmware_family == "buddy")
                    self._paused = False
            elif action == "cancel":
                if job.state != "cancelling":
                    log.info("the printer cancelled the print")
                    self._cancelled = True
                    self._paused = False
                    self._set_state(job, "cancelling")
            else:
                return
            self._cv.notify_all()

    def cancel(self) -> None:
        with self._cv:
            job = self._job
            if job is None or not job.active:
                raise JobError("no print is running")
            if job.state == "cancelling":
                return
            self._cancelled = True
            self._paused = False
            self._set_state(job, "cancelling")
            self._cv.notify_all()
            printer = self._printer
        # A heat-up (M109/M190) blocks send() for minutes; M108 makes the firmware give up on it.
        if printer is not None:
            try:
                printer.interrupt_wait()
            except PrinterError:
                pass

    def restart(self) -> JobState:
        with self._lock:
            job = self._job
            if job is None:
                raise JobError("nothing to print again")
            return self.start(job.path, name=job.name, file_id=job.file_id, estimated_seconds=job.estimated_seconds,
                              bed=self._bed, cancel_gcode=self._job_cancel_gcode)

    def stop(self) -> None:
        with self._cv:
            self._cancelled = True
            self._paused = False
            self._cv.notify_all()
            thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=5)

    def add_energy(self, watt_hours: float) -> None:
        with self._lock:
            job = self._job
            if job is None or not job.active or watt_hours <= 0:
                return
            job.energy_wh = (job.energy_wh or 0.0) + watt_hours

    # ---- streaming -------------------------------------------------------------------

    def _run(self, job: JobState, printer: Printer) -> None:
        try:
            self._stream(job, printer)
        except PrinterError as exc:
            self._finish(job, printer, "error", str(exc))
            return
        except OSError as exc:
            self._finish(job, printer, "error", f"could not read {job.path}: {exc}")
            return
        except Exception as exc:  # noqa: BLE001 - never leave a job stuck in "printing"
            log.exception("print job failed")
            self._finish(job, printer, "error", f"{type(exc).__name__}: {exc}")
            return

        if self._cancelled:
            self._run_cancel_gcode(printer)
            self._finish(job, printer, "cancelled")
        else:
            self._finish(job, printer, "finished")

    def _stream(self, job: JobState, printer: Printer) -> None:
        job.total_lines, job.total_layers, job.total_bytes = scan_file(job.path)
        self._last_extrusion = last_extrusion_line(job.path, job.total_lines)
        self._publish(job, force=True)
        with open(job.path, "rb") as handle:
            for raw in handle:
                if self._cancelled:
                    return
                consumed = job.line + 1
                stripped = raw.strip()
                if stripped.startswith(b";"):
                    with self._lock:
                        job.line = consumed
                        if stripped.startswith(_LAYER_MARKER_PREFIXES):
                            job.layer += 1
                            if self._print_started_at is None:
                                self._print_started_at = self._elapsed()
                                job.activity = None
                            self._publish(job, force=True)
                    continue
                command = protocol.strip_comment(raw.decode("utf-8", "replace"))
                if not command:
                    with self._lock:
                        job.line = consumed
                    continue
                self._wait_while_paused(job, printer)
                if self._cancelled:
                    return
                self._track_m73(command)
                self._track_modes(command)
                self._track_activity(job, command)
                if self._part_is_done(job) and leaves_the_part(command):
                    self._finish_part(job, printer)
                printer.send(command)
                with self._lock:
                    job.line = consumed
                    job.bytes_sent += len(raw)
                self._poll_temperature(printer)
                self._publish(job)

    def _wait_while_paused(self, job: JobState, printer: Printer) -> None:
        with self._cv:
            if not self._paused:
                return
            self._pause_began = time.monotonic()
            activity = job.activity
            job.activity = "pausing"
            self._publish(job, force=True)
        try:
            self._run_pause_script(printer)
        finally:
            with self._cv:
                job.activity = activity
                self._set_state(job, "paused")
        with self._cv:
            while self._paused and not self._cancelled:
                self._cv.wait(0.25)
            if self._cancelled:
                self._end_pause(job)
                return
            self._set_state(job, "printing", publish=False)
            job.activity = "resuming"
            self._publish(job, force=True)
        try:
            self._run_resume_script(printer)
        finally:
            with self._cv:
                job.activity = activity
                self._end_pause(job)
                self._publish(job, force=True)

    def _part_is_done(self, job: JobState) -> bool:
        return not self._part_finished and self._last_extrusion is not None and job.line >= self._last_extrusion

    def _finish_part(self, job: JobState, printer: Printer) -> None:
        """The last extrusion is out and the next move leaves the part: let the moves finish and
        tell the listener, which takes the closing timelapse frame while the part is in view."""
        self._part_finished = True
        printer.send("M400")
        if self.on_part_finished is not None:
            try:
                self.on_part_finished(copy.copy(job))
            except Exception:  # noqa: BLE001 - a listener must not end the print
                log.exception("part finished listener failed")

    def _end_pause(self, job: JobState) -> None:
        if self._pause_began is not None:
            self._paused_total += time.monotonic() - self._pause_began
            self._pause_began = None
        self._printer_paused = self._printer_resumed = False

    def _run_pause_script(self, printer: Printer) -> None:
        if printer.firmware_family in PRUSA_FAMILIES:
            # The firmware parks, cools and keeps the print alive in its paused state; nothing to
            # do when it paused by itself.
            if not self._printer_paused:
                printer.send("M601")
            return
        printer.send("M400")
        self._pause_position = None
        for line in printer.send("M114"):
            message = protocol.parse(line)
            if message.kind == "position":
                self._pause_position = message.position
        printer.send("M83")
        printer.send(f"G1 E-{PAUSE_RETRACT_MM:g} F2400")
        printer.send("G91")
        printer.send(f"G1 Z{PAUSE_LIFT_MM:g} F600")
        printer.send("G90")
        park = self._park_position()
        if park is not None:
            printer.send(f"G1 X{park[0]:.1f} Y{park[1]:.1f} F6000")

    def _run_resume_script(self, printer: Printer) -> None:
        family = printer.firmware_family
        if family in PRUSA_FAMILIES:
            if self._printer_resumed:
                return  # Buddy has reheated and returned already; M602 would be a no-op
            self._resumed.clear()
            # The MK3 answers M602 only once it is back in position; Buddy answers at once and
            # reports "action:resume" when it accepts G-code again.
            printer.send("M602", timeout=RESUME_TIMEOUT)
            if family == "buddy" and not self._wait_for_resume():
                log.warning("no action:resume from the printer within %g s, streaming anyway", RESUME_TIMEOUT)
            return
        position = self._pause_position
        printer.send("G90")
        if position and "X" in position and "Y" in position:
            printer.send(f"G1 X{position['X']:.3f} Y{position['Y']:.3f} F6000")
        if position and "Z" in position:
            printer.send(f"G1 Z{position['Z']:.3f} F600")
        printer.send("M83")
        printer.send(f"G1 E{PAUSE_RETRACT_MM:g} F2400")
        if position and "E" in position:
            printer.send(f"G92 E{position['E']:.5f}")
        printer.send("M83" if self._relative_extrusion else "M82")
        printer.send("G91" if self._relative_positioning else "G90")
        if self._feedrate:
            printer.send(f"G1 F{self._feedrate:g}")

    def _wait_for_resume(self) -> bool:
        deadline = time.monotonic() + RESUME_TIMEOUT
        while not self._resumed.is_set():
            if self._cancelled or time.monotonic() >= deadline:
                return False
            self._resumed.wait(0.25)
        return True

    def _park_position(self) -> tuple[float, float] | None:
        """The back left corner of the bed, where the head is out of the way; none for a round bed."""
        bed = self._bed
        if not bed or bed.get("centered") or not bed.get("x") or not bed.get("y"):
            return None
        return PAUSE_PARK_INSET_MM, float(bed["y"]) - PAUSE_PARK_INSET_MM

    def _track_modes(self, command: str) -> None:
        """Positioning and extrusion modes and the feedrate, so the resume script can restore them."""
        code = command.split(" ", 1)[0].upper()
        if code == "G90":
            self._relative_positioning = False
        elif code == "G91":
            self._relative_positioning = True
        elif code == "M82":
            self._relative_extrusion = False
        elif code == "M83":
            self._relative_extrusion = True
        elif code in ("G0", "G1", "G2", "G3"):
            match = _FEEDRATE_RE.search(command)
            if match:
                self._feedrate = float(match.group(1))

    def _track_m73(self, command: str) -> None:
        percent = _M73_PERCENT_RE.match(command)
        remaining = _M73_REMAINING_RE.match(command)
        if percent is None and remaining is None:
            return
        with self._lock:
            if percent is not None:
                self._m73_progress = min(1.0, float(percent.group(1)) / 100.0)
            if remaining is not None:
                seconds = float(remaining.group(1)) * 60.0
                share = float(percent.group(1)) if percent is not None else None
                expected = seconds * share / (100.0 - share) if share is not None and 0 < share < 100 else None
                self._m73 = (seconds, self._elapsed(), expected)

    def _track_activity(self, job: JobState, command: str) -> None:
        """Published before the command goes out, because a heat-up blocks send() for minutes."""
        if job.activity is None:
            return
        activity = activity_of(command)
        if activity is None or activity == job.activity:
            return
        with self._lock:
            job.activity = activity
            self._publish(job, force=True)

    def _poll_temperature(self, printer: Printer) -> None:
        """send() holds the port most of the time, so the poller in Printer never gets a turn."""
        if printer.state.capabilities.get("AUTOREPORT_TEMP"):
            return
        now = time.monotonic()
        if now - self._last_temperature >= printer.temperature_interval:
            self._last_temperature = now
            printer.send("M105")

    def _run_cancel_gcode(self, printer: Printer) -> None:
        for command in self._job_cancel_gcode or self.cancel_gcode:
            try:
                printer.send(command)
            except PrinterError as exc:
                log.warning("cancel script stopped at %r: %s", command, exc)
                return

    def _finish(self, job: JobState, printer: Printer, state: str, error: str | None = None) -> None:
        with self._lock:
            self._finished = time.monotonic()
            job.finished_at = time.time()
            job.error = error
            self._set_state(job, state, publish=False)
            job.activity = None
            if state == "finished":
                job.progress = 1.0
            if printer.state.status in ("printing", "paused"):
                printer.set_status("idle")
            self._publish(job, force=True)
        log.info("print %s %s%s", job.name, state, f": {error}" if error else "")

    # ---- state -----------------------------------------------------------------------

    def _set_state(self, job: JobState, state: str, *, publish: bool = True) -> None:
        job.state = state
        printer = self._printer
        if printer is not None and state in ("printing", "paused") and printer.state.status != "halted":
            printer.set_status(state)
        if publish:
            self._publish(job, force=True)

    def _elapsed(self) -> float:
        end = self._finished if self._finished is not None else time.monotonic()
        paused = self._paused_total
        if self._pause_began is not None:
            paused += end - self._pause_began
        return max(0.0, end - self._started - paused)

    def _refresh_times(self, job: JobState) -> None:
        elapsed = self._elapsed()
        job.elapsed = elapsed
        if job.state != "finished":
            if self._m73_progress is not None:
                job.progress = self._m73_progress
            elif job.total_bytes:
                job.progress = min(1.0, job.bytes_sent / job.total_bytes)
        if not job.active:
            job.remaining = 0.0 if job.state == "finished" else None
            job.remaining_source = None
            return
        job.remaining, job.remaining_source = self._estimate_remaining(job, elapsed)

    def _estimate_remaining(self, job: JobState, elapsed: float) -> tuple[float | None, str | None]:
        started = self._print_started_at
        if self._m73 is not None:
            remaining, seen_at, expected = self._m73
            if started is None:
                return remaining, "m73"  # the slicer's clock has not started: heating is not in its figure
            left = remaining * pace_factor(seen_at - started, expected) - (elapsed - seen_at)
            if left > 0:
                return left, "m73"
            # The slicer's estimate has run out while the print goes on; the pace takes over.
        progress = job.progress
        by_pace = elapsed / progress - elapsed if progress >= 0.02 and elapsed >= 30 else None
        if not job.estimated_seconds:
            by_slicer = None
        elif started is None:
            by_slicer = float(job.estimated_seconds)
        else:
            by_slicer = max(0.0, job.estimated_seconds - elapsed)
        if by_slicer is not None and by_pace is not None:
            # Trust the slicer early on and the observed pace towards the end.
            return (1 - progress) * by_slicer + progress * by_pace, "slicer"
        if by_slicer is not None:
            return by_slicer, "slicer"
        if by_pace is not None:
            return by_pace, "progress"
        return None, None

    def _publish(self, job: JobState, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self._last_publish < self.publish_interval:
            return
        self._last_publish = now
        if self.on_state is None:
            return
        with self._lock:
            self._refresh_times(job)
            snapshot = copy.copy(job)
        try:
            self.on_state(snapshot)
        except Exception:  # noqa: BLE001 - a listener must not stop the print
            log.exception("job listener failed")
