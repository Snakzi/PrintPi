"""Bed level visualizer: probes the bed and keeps the last mesh the printer reported.

A probe sends the configured G-code lines (heating, homing, G29, the report
command) from its own thread, because that takes minutes and the bridge worker
has to stay free for disconnect and emergency stop. The mesh itself is read from
the serial stream, so a mesh the printer prints on its own, at print start or
after G81 in the terminal, is picked up as well.

While a probe runs the status carries the current line of the sequence and the
points probed so far, counted from what the firmware prints per point.
"""

from __future__ import annotations

import re
import threading
import time

from printpi_daemon.job import ACTIVE_STATES
from printpi_daemon.plugins import PluginBase, PluginError

from .mesh import MeshParser, spread

PROBE_TIMEOUT = 900.0  # a full-bed G29 on a large printer; "busy" keepalives extend it anyway

# One line per probed point, by firmware. UBL is the only one that says how many there are.
_POINT_WITH_TOTAL_RE = re.compile(r"Probing mesh point (\d+)/(\d+)")  # Marlin UBL
_POINT_RES = (
    re.compile(r"Probe classified as .*\bOK\b"),  # Prusa Buddy, one accepted tap of the load cell
    re.compile(r"^(?:echo:)?Bed X: ?-?\d"),  # Marlin ABL with G29 V3 and up
    re.compile(r"^(?://\s*)?probe at -?[\d.]+,-?[\d.]+ is z="),  # Klipper
)


class Plugin(PluginBase):
    def start(self) -> None:
        if float(self.settings.get("tolerance", 0.1)) <= 0:
            raise PluginError("tolerance must be above 0")
        self._parser = MeshParser()
        self._probing = False
        self._error: str | None = None
        self._stop_requested = False
        self._job_active = False
        self._flat_seen = False
        self._step: str | None = None
        self._step_index = 0
        self._step_count = 0
        self._points = 0
        self._points_total: int | None = None

    def stop(self) -> None:
        self._stop_requested = True

    def apply_settings(self, settings: dict) -> None:
        # Another sequence may probe another number of points; the learned total is for the old one.
        if settings.get("gcode") != self.settings.get("gcode") and "probe_points" in self.state:
            del self.state["probe_points"]
            self.save_state()
        super().apply_settings(settings)

    def handle(self, action: str, value) -> None:
        if action != "probe":
            raise PluginError(f"unknown action {action!r}")
        if self._probing:
            raise PluginError("a probe is already running")
        if self._job_active:
            raise PluginError("a print is running")
        self._probing, self._error, self._flat_seen = True, None, False
        threading.Thread(target=self._probe, name="bed-level-probe", daemon=True).start()

    def on_printer_state(self, state: dict) -> None:
        job = state.get("job") or {}
        self._job_active = job.get("state") in ACTIVE_STATES

    def on_serial_line(self, direction: str, line: str) -> None:
        if direction != "rx":
            return
        if self._probing and self._count_point(line):
            self.status_changed()
        mesh = self._parser.feed(line)
        if mesh is None:
            return
        if mesh.is_flat:
            self._flat_seen = True
            return
        self.state["mesh"] = mesh.to_dict()
        self.state["measured_at"] = time.time()
        self.state["source"] = "probe" if self._probing else "serial"
        self.save_state()
        self.status_changed()

    def status(self) -> dict:
        mesh = dict(self.state.get("mesh") or {})
        area = self._area()
        if mesh and not mesh.get("x") and area:
            x_min, x_max, y_min, y_max = area
            mesh["x"], mesh["y"] = spread(x_min, x_max, mesh["cols"]), spread(y_min, y_max, mesh["rows"])
        return {
            "mesh": {
                "probing": self._probing,
                "error": self._error,
                "tolerance": float(self.settings.get("tolerance", 0.1)),
                "measured_at": self.state.get("measured_at"),
                "source": self.state.get("source"),
                "step": self._step,
                "step_index": self._step_index,
                "step_count": self._step_count,
                "points": self._points,
                "points_total": self._points_total or self.state.get("probe_points"),
                **mesh,
            },
        }

    def commands(self) -> list[str]:
        """The configured sequence, one command per line; blank lines and comments are skipped."""
        lines = (line.split(";", 1)[0].strip() for line in str(self.settings.get("gcode", "")).splitlines())
        return [line for line in lines if line]

    def _area(self) -> tuple[float, float, float, float] | None:
        """The probed area in mm from the settings, for reports that do not say where their points are."""
        x_min, x_max, y_min, y_max = (float(self.settings.get(key) or 0) for key in ("x_min", "x_max", "y_min", "y_max"))
        if x_max > x_min and y_max > y_min:
            return x_min, x_max, y_min, y_max
        return None

    def _count_point(self, line: str) -> bool:
        match = _POINT_WITH_TOTAL_RE.search(line)
        if match:
            self._points, self._points_total = int(match.group(1)), int(match.group(2))
            return True
        if any(pattern.search(line) for pattern in _POINT_RES):
            self._points += 1
            return True
        return False

    def _probe(self) -> None:
        started = time.time()
        most_points = 0
        try:
            commands = self.commands()
            if not commands:
                self._error = "No G-code configured"
                return
            self._step_count = len(commands)
            for index, command in enumerate(commands, 1):
                if self._stop_requested:
                    return
                self._step, self._step_index, self._points = command, index, 0
                self.status_changed()
                self.send_gcode(command, timeout=PROBE_TIMEOUT)
                most_points = max(most_points, self._points)
            if (self.state.get("measured_at") or 0) < started:
                self._error = ("The printer reported a mesh without values" if self._flat_seen
                               else "The printer did not report a mesh")
        except Exception as exc:  # noqa: BLE001 - shown in the UI instead of killing the thread
            self._error = str(exc) or type(exc).__name__
        finally:
            # The count of the last run is next time's total for firmwares that do not announce one.
            if most_points and self._points_total is None:
                self.state["probe_points"] = most_points
                self.save_state()
            self._probing = False
            self._step, self._step_index, self._step_count, self._points = None, 0, 0, 0
            self.status_changed()
