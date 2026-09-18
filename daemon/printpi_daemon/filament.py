"""Filament load, unload and change as a walkthrough PrintPi drives step by step.

The firmware's own load (M701 on Marlin and Buddy) does the mechanics well enough,
but it ends in a question on the printer's display that no host can answer over
serial, and it says nothing about its progress on the wire. So the runner does the
steps itself with plain G-codes: heat, push the filament in at the printer's own
speeds, purge, ask whether the colour runs clean, and for an unload shape the tip
with the printer's ramming sequence before pulling the filament out. Every step and
every question lives in PrintPi's state, so the touch panel and the web app show
the same walkthrough and either one can answer. The lengths and speeds come from
the printer profile, so a bowden printer loads its 400 mm and an MK4S Prusa's
30 + 50 mm.

On Buddy firmware the runner also tells the printer which filament is in (M865 with
L0), so its display and a print from its USB drive agree with PrintPi, and it
blocks the extruder stall detection (M591) during a load the way the firmware does
for its own. The printer's autoload has to be off on such printers: it would start
a load of its own the moment its sensor sees the filament.
"""

from __future__ import annotations

import copy
import logging
import re
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Callable

from .printer import Printer, PrinterError

log = logging.getLogger("printpi.filament")

ACTIONS = ("load", "unload", "change")
# The walkthrough of each action, in order; the runner reports which one it is on.
STEPS = {
    "load": ("heating", "insert", "loading", "purging", "check", "done"),
    "unload": ("heating", "unloading", "remove", "done"),
    # A change heats twice: for the filament coming out, then for the one going in.
    "change": ("heating", "unloading", "remove", "heating", "insert", "loading", "purging", "check", "done"),
}
# Steps that wait for the user: Continue on insert and remove, an answer on check.
WAITING_STEPS = ("insert", "remove", "check")
END_STEPS = ("done", "cancelled", "error")
ANSWERS = ("yes", "purge")
HEAT_TIMEOUT = 600.0
HEAT_TOLERANCE = 3.0  # °C below the target that counts as reached, like the firmware's own loads
# Buddy's preset filament types, which M865 S"…" selects by name; anything else becomes a custom type.
BUDDY_PRESETS = {"PLA", "PETG", "ASA", "PC", "PVB", "ABS", "HIPS", "PP", "FLEX", "PA"}
BUDDY_ALIASES = {"TPU": "FLEX"}
BUDDY_NAME_LENGTH = 7  # the firmware's name buffer, terminator excluded
BUDDY_PREHEAT_TEMP = 170
# A direct drive extruder's moves: [mm, mm/min] per move, positive pushes filament in.
DEFAULT_MOVES = {
    "load": [[30, 360], [50, 1200]],
    "purge": [40, 180],
    "unload": [[5, 600], [-20, 3000], [-80, 1500]],
}

_NAME_RE = re.compile(r"[^A-Z0-9+-]")

StateListener = Callable[["FilamentState"], None]
RecordListener = Callable[[str, dict | None], None]


class FilamentError(Exception):
    pass


class _Cancelled(Exception):
    pass


@dataclass
class FilamentState:
    action: str  # load | unload | change
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    step: str = "heating"  # one of STEPS[action], or cancelled | error
    steps: tuple[str, ...] = ()
    step_index: int = 0  # where in `steps` the walkthrough is; a change heats twice, so the name alone is ambiguous
    waiting: bool = False  # the step needs Continue or an answer
    progress: float | None = None  # of the current step, 0..1
    step_started_at: float = field(default_factory=time.time)
    step_duration: float | None = None  # seconds a motion step takes, so the UI can animate between polls
    spool: dict | None = None  # {id, name, material, color} as the app passed it
    material: str | None = None
    nozzle: int | None = None  # the temperature of the filament being loaded, or unloaded
    target: int | None = None  # what the hotend is heating to right now: the old filament's or the new one's
    temperature: float | None = None  # the hotend while heating
    purges: int = 0
    error: str | None = None
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None

    @property
    def active(self) -> bool:
        return self.step not in END_STEPS

    def to_dict(self) -> dict:
        data = asdict(self)
        data["steps"] = list(self.steps)
        return data


def buddy_filament_gcode(material: str | None, nozzle: int | None) -> str:
    """The M865 that tells a Buddy printer what is loaded: a preset by name, else a custom type
    with the material's temperatures, named after the material as far as its 7 characters go."""
    name = _NAME_RE.sub("", (material or "").upper().replace(" ", "-").replace("_", "-"))
    preset = BUDDY_ALIASES.get(name, name)
    if preset in BUDDY_PRESETS:
        return f'M865 S"{preset}" L0'
    name = name[:BUDDY_NAME_LENGTH] or "CUSTOM"
    temp = int(nozzle or 215)
    return f'M865 X R N"{name}" T{temp} P{min(BUDDY_PREHEAT_TEMP, temp)} L0'


def moves_duration(moves: list[list[float]]) -> float:
    """Seconds a list of [mm, mm/min] moves takes, for the progress the UI animates."""
    return sum(abs(mm) / feed * 60.0 for mm, feed in moves if feed > 0)


def _moves(value, fallback: list[list[float]]) -> list[list[float]]:
    if not isinstance(value, list):
        return [list(move) for move in fallback]
    moves = []
    for move in value:
        try:
            mm, feed = float(move[0]), float(move[1])
        except (TypeError, ValueError, IndexError):
            continue
        if mm and feed > 0:
            moves.append([mm, feed])
    return moves or [list(move) for move in fallback]


class FilamentRunner:
    """Runs one load, unload or change at a time on its own thread; the bridge drives it."""

    def __init__(
        self,
        printer_provider: Callable[[], Printer],
        *,
        on_state: StateListener | None = None,
        on_record: RecordListener | None = None,
    ) -> None:
        self._printer_of = printer_provider
        self.on_state = on_state
        self.on_record = on_record
        self._lock = threading.RLock()
        self._cv = threading.Condition(self._lock)
        self._state: FilamentState | None = None
        self._thread: threading.Thread | None = None
        self._proceed = False
        self._answer: str | None = None
        self._cancelled = False
        self._moves: dict = {}
        self._unload_nozzle: int | None = None
        self._step_began = 0.0  # monotonic, for the progress of a motion step

    # ---- what the bridge calls ------------------------------------------------------

    @property
    def state(self) -> FilamentState | None:
        with self._lock:
            if self._state is None:
                return None
            self._refresh_progress(self._state)
            return copy.copy(self._state)

    @property
    def active(self) -> bool:
        with self._lock:
            return self._state is not None and self._state.active

    def start(self, action: str, *, spool: dict | None = None, material: str | None = None,
              nozzle: int | None = None, unload_nozzle: int | None = None, moves: dict | None = None) -> FilamentState:
        """nozzle is the temperature of the filament going in, unload_nozzle of the one coming out
        (a change heats to the higher one first); moves are the profile's load, purge and unload lists."""
        if action not in ACTIONS:
            raise FilamentError(f"unknown filament action {action!r}")
        with self._lock:
            if self._state is not None and self._state.active:
                raise FilamentError("a filament change is already running")
            printer = self._printer_of()
            if not printer.connected:
                raise FilamentError("printer is not connected")
            if action != "unload" and not nozzle:
                raise FilamentError("no temperature for the filament to load")
            moves = moves if isinstance(moves, dict) else {}
            self._moves = {
                "load": _moves(moves.get("load"), DEFAULT_MOVES["load"]),
                "purge": _moves([moves.get("purge")] if moves.get("purge") else None, [DEFAULT_MOVES["purge"]]),
                "unload": _moves(moves.get("unload"), DEFAULT_MOVES["unload"]),
            }
            self._unload_nozzle = int(unload_nozzle) if unload_nozzle else (int(nozzle) if nozzle else None)
            self._proceed = self._cancelled = False
            self._answer = None
            state = FilamentState(
                action=action,
                steps=STEPS[action],
                spool=self._spool_summary(spool),
                material=str(material) if material else (spool or {}).get("material"),
                nozzle=int(nozzle) if nozzle else self._unload_nozzle,
            )
            self._state = state
            self._thread = threading.Thread(target=self._run, args=(state, printer), name="filament", daemon=True)
            self._thread.start()
            self._publish(state)
            log.info("filament %s started (%s)", action, state.material or "unknown material")
            return copy.copy(state)

    def proceed(self) -> None:
        """Continue after the user inserted or pulled out the filament."""
        with self._cv:
            state = self._state
            if state is None or not state.active or state.step not in ("insert", "remove"):
                raise FilamentError("nothing to continue")
            self._proceed = True
            self._cv.notify_all()

    def answer(self, answer: str) -> None:
        """The colour check: yes ends the load, purge pushes another purge length through."""
        if answer not in ANSWERS:
            raise FilamentError(f"unknown answer {answer!r}")
        with self._cv:
            state = self._state
            if state is None or not state.active or state.step != "check":
                raise FilamentError("no question is open")
            self._answer = answer
            self._cv.notify_all()

    def cancel(self) -> None:
        with self._cv:
            state = self._state
            if state is None or not state.active:
                raise FilamentError("no filament change is running")
            self._cancelled = True
            self._cv.notify_all()

    def stop(self) -> None:
        """Daemon shutdown: end the walkthrough without talking to the printer."""
        with self._cv:
            self._cancelled = True
            self._cv.notify_all()
            thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=5)

    # ---- the walkthrough -----------------------------------------------------------

    def _run(self, state: FilamentState, printer: Printer) -> None:
        buddy = printer.firmware_family == "buddy"
        try:
            if state.action in ("unload", "change"):
                self._unload_phase(state, printer)
            if state.action in ("load", "change"):
                self._load_phase(state, printer, buddy)
            self._end(state, printer, "done", buddy=buddy)
        except _Cancelled:
            self._end(state, printer, "cancelled", buddy=buddy)
        except PrinterError as exc:
            self._end(state, printer, "error", str(exc), buddy=buddy)
        except Exception as exc:  # noqa: BLE001 - never leave the walkthrough stuck
            log.exception("filament %s failed", state.action)
            self._end(state, printer, "error", f"{type(exc).__name__}: {exc}", buddy=buddy)

    def _unload_phase(self, state: FilamentState, printer: Printer) -> None:
        self._heat(state, printer, self._unload_nozzle or state.nozzle or 0)
        self._motion(state, printer, "unloading", self._moves["unload"])
        if state.action == "unload":
            printer.send("M104 S0")
        self._record("unloaded", None)
        self._wait_for_user(state, printer, "remove")

    def _load_phase(self, state: FilamentState, printer: Printer, buddy: bool) -> None:
        if buddy:
            printer.send("M591 S0")  # the loadcell would read the push into an empty extruder as a stall
        self._heat(state, printer, state.nozzle or 0)
        self._wait_for_user(state, printer, "insert")
        self._heat(state, printer, state.nozzle or 0)  # the printer's safety timer may have cooled it meanwhile
        self._motion(state, printer, "loading", self._moves["load"])
        while True:
            self._motion(state, printer, "purging", self._moves["purge"])
            with self._lock:
                state.purges += 1
            if self._ask(state, printer) == "yes":
                break
        if buddy:
            printer.send(buddy_filament_gcode(state.material, state.nozzle))
        self._record("loaded", state.spool)

    def _heat(self, state: FilamentState, printer: Printer, target: int) -> None:
        if target <= 0:
            raise FilamentError("no temperature to heat to")
        self._check_cancelled()
        reading = printer.state.temperatures.get("T0")
        if reading is None or (reading.target or 0) != target:
            printer.send(f"M104 S{target}")  # a change drops from the old filament's temperature to the new one
        if reading is not None and reading.actual >= target - HEAT_TOLERANCE:
            return
        start = reading.actual if reading is not None else 20.0
        self._set_step(state, "heating", temperature=start, target=target)
        deadline = time.monotonic() + HEAT_TIMEOUT
        last_poll = time.monotonic()
        while True:
            reading = printer.state.temperatures.get("T0")
            actual = reading.actual if reading is not None else start
            if actual >= target - HEAT_TOLERANCE:
                return
            if time.monotonic() > deadline:
                raise FilamentError(f"the hotend did not reach {target} °C")
            with self._lock:
                state.temperature = actual
                state.progress = max(0.0, min(1.0, (actual - start) / (target - start))) if target > start else 1.0
            self._publish(state)
            self._sleep(0.5)
            if not printer.state.capabilities.get("AUTOREPORT_TEMP") and time.monotonic() - last_poll >= printer.temperature_interval:
                last_poll = time.monotonic()
                printer.send("M105")

    def _motion(self, state: FilamentState, printer: Printer, step: str, moves: list[list[float]]) -> None:
        self._check_cancelled()
        self._set_step(state, step, duration=moves_duration(moves))
        printer.send("M83")
        try:
            for mm, feed in moves:
                self._check_cancelled()
                printer.send(f"G1 E{mm:g} F{feed:g}")
            printer.send("M400")  # the ok of a move only says it was queued
        finally:
            printer.send("M82")

    def _wait_for_user(self, state: FilamentState, printer: Printer, step: str) -> None:
        with self._cv:
            self._proceed = False
            self._set_step(state, step, waiting=True)
            while not self._proceed:
                if self._cancelled:
                    raise _Cancelled()
                self._cv.wait(0.5)

    def _ask(self, state: FilamentState, printer: Printer) -> str:
        with self._cv:
            self._answer = None
            self._set_step(state, "check", waiting=True)
            while self._answer is None:
                if self._cancelled:
                    raise _Cancelled()
                self._cv.wait(0.5)
            return self._answer

    def _end(self, state: FilamentState, printer: Printer, step: str, error: str | None = None, *, buddy: bool = False) -> None:
        for command in (["M591 R"] if buddy and state.action != "unload" else []) + ["M104 S0"]:
            try:
                printer.send(command)
            except PrinterError as exc:
                log.warning("could not run %r after the filament %s: %s", command, state.action, exc)
                break
        with self._lock:
            state.error = error
            state.finished_at = time.time()
            self._set_step(state, step, publish=False)
            state.progress = None
            state.waiting = False
        self._publish(state)
        log.info("filament %s %s%s", state.action, step, f": {error}" if error else "")

    # ---- helpers ---------------------------------------------------------------------

    def _check_cancelled(self) -> None:
        with self._lock:
            if self._cancelled:
                raise _Cancelled()

    def _sleep(self, seconds: float) -> None:
        with self._cv:
            if self._cancelled:
                raise _Cancelled()
            self._cv.wait(seconds)
            if self._cancelled:
                raise _Cancelled()

    def _set_step(self, state: FilamentState, step: str, *, waiting: bool = False, duration: float | None = None,
                  temperature: float | None = None, target: int | None = None, publish: bool = True) -> None:
        with self._lock:
            state.step = step
            state.step_index = self._index_of(state, step)
            state.waiting = waiting
            state.step_started_at = time.time()
            state.step_duration = duration
            state.progress = 0.0 if duration else None
            state.temperature = temperature
            state.target = target
            self._step_began = time.monotonic()
        if publish:
            self._publish(state)

    @staticmethod
    def _index_of(state: FilamentState, step: str) -> int:
        """The position of the step, counting on from the current one; done is the last, a cancel or
        an error stays where the walkthrough was."""
        if step == "done":
            return len(state.steps) - 1
        if step in END_STEPS:
            return state.step_index
        for index in range(state.step_index, len(state.steps)):
            if state.steps[index] == step:
                return index
        return state.step_index

    def _refresh_progress(self, state: FilamentState) -> None:
        if state.active and state.step_duration:
            state.progress = min(1.0, (time.monotonic() - self._step_began) / state.step_duration)

    def _record(self, event: str, spool: dict | None) -> None:
        if self.on_record is None:
            return
        try:
            self.on_record(event, spool)
        except Exception:  # noqa: BLE001 - a listener must not stop the walkthrough
            log.exception("filament record listener failed")

    def _publish(self, state: FilamentState) -> None:
        if self.on_state is None:
            return
        with self._lock:
            self._refresh_progress(state)
            snapshot = copy.copy(state)
        try:
            self.on_state(snapshot)
        except Exception:  # noqa: BLE001
            log.exception("filament listener failed")

    @staticmethod
    def _spool_summary(spool: dict | None) -> dict | None:
        if not isinstance(spool, dict) or spool.get("id") is None:
            return None
        return {
            "id": spool.get("id"),
            "name": str(spool.get("name") or ""),
            "material": str(spool.get("material") or "") or None,
            "color": str(spool.get("color") or "") or None,
        }
