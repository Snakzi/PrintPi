"""Parser for the bed mesh reports Marlin and Prusa firmwares print.

Known dialects:

- Marlin bilinear and mesh bed leveling ("Bilinear Leveling Grid:" or "Measured
  points:" after G29 T and M420 V): column labels, then one row per Y index
  counting up from the front of the bed, missing points as "====".
- Marlin UBL ("Bed Topography Report:" after G29 T and M420 V, also what Prusa
  Buddy prints): rows count down from the back, "|" separators, the current
  position in brackets, the corner coordinates in mm around the grid, missing
  points as ".".
- UBL CSV ("Bed Topography Report for CSV:"): tab separated rows counting down.
- Prusa i3 MK3 (G81): "Measured points:" followed by unlabelled rows counting
  down from the back.

MeshParser takes one line at a time and returns a Mesh when a block is complete,
so it works on the live serial stream as well as on the reply of one command.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from printpi_daemon import protocol

# Lines the firmware may slip into a report without ending it: temperature autoreports,
# host keepalives and "wait".
_CHATTER = ("temperature", "busy", "wait")

# Header line -> (format, rows count down from the back of the bed when unlabelled).
_HEADERS: tuple[tuple[re.Pattern[str], str, bool], ...] = (
    (re.compile(r"^Subdivided with CATMULL ROM Leveling Grid:?$"), "skip", False),
    (re.compile(r"^Bilinear Leveling Grid(?: Corrected)?:?$"), "bilinear", False),
    (re.compile(r"^Bed Topography Report for CSV:?$"), "ubl_csv", True),
    (re.compile(r"^Bed Topography Report(?: for LCD)?:?$"), "ubl", True),
    (re.compile(r"^Mesh Bed Level data:?$"), "mbl", False),
    (re.compile(r"^Measured points:?$"), "mbl", True),
)
_ROW_CHARS_RE = re.compile(r"^[\s\d.+\-=|\[\]NAna]+$")
_LABEL_RE = re.compile(r"^\s*(\d+)(?:\s*\||\s+)(.*)$")
_TOKEN_RE = re.compile(r"[-+]?\d+\.\d+|=+|NAN|nan|\.|\d+")
_VALUE_RE = re.compile(r"^[-+]?\d+\.\d+$")
_CORNER_RE = re.compile(r"\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)")


@dataclass
class Mesh:
    """Probed heights in mm as z[y][x], y counting up from the front of the bed."""

    z: list[list[float | None]]
    format: str
    x: list[float] | None = None  # probe positions in mm when the report says
    y: list[float] | None = None

    @property
    def rows(self) -> int:
        return len(self.z)

    @property
    def cols(self) -> int:
        return len(self.z[0]) if self.z else 0

    @property
    def is_flat(self) -> bool:
        """Every point the same, what a firmware prints before it ever probed."""
        values = {value for row in self.z for value in row if value is not None}
        return len(values) <= 1

    def to_dict(self) -> dict:
        return {"rows": self.rows, "cols": self.cols, "z": self.z, "x": self.x, "y": self.y, "format": self.format}


class MeshParser:
    def __init__(self) -> None:
        self._format: str | None = None
        self._descending = False
        self._rows: list[tuple[int | None, list[float | None]]] = []
        self._corners: list[tuple[float, float]] = []

    @property
    def in_block(self) -> bool:
        return self._format is not None

    def feed(self, line: str) -> Mesh | None:
        """Take the next line from the printer; returns a mesh when one just ended."""
        text = line.strip()
        if text.startswith("echo:"):
            text = text[5:].strip()
        if self._format is not None and protocol.parse(line).kind in _CHATTER:
            return None
        result = None
        if self._format is not None and not self._continue(text):
            result = self._finish()
        header = self._header(text)
        if header is not None:
            self._format, self._descending = header
            self._rows, self._corners = [], []
        return result

    @staticmethod
    def _header(text: str) -> tuple[str, bool] | None:
        for pattern, name, descending in _HEADERS:
            if pattern.match(text):
                return name, descending
        return None

    def _continue(self, text: str) -> bool:
        """Consume a line inside a block; False when the line does not belong to it."""
        if not text or re.fullmatch(r"\|?", text):
            return True  # UBL separates rows with "   |" and pads the report with blank lines
        corners = _CORNER_RE.findall(text)
        if corners:
            self._corners.extend((float(x), float(y)) for x, y in corners)
            return True
        if not _ROW_CHARS_RE.match(text):
            return False
        row = _parse_row(text)
        if row is not None and row[1]:
            self._rows.append(row)
        return True

    def _finish(self) -> Mesh | None:
        fmt, rows, corners = self._format, self._rows, self._corners
        self._format, self._rows, self._corners = None, [], []
        if fmt == "skip" or len(rows) < 2 or len({len(values) for _, values in rows}) != 1 or len(rows[0][1]) < 2:
            return None
        labels = [label for label, _ in rows]
        if all(label is not None for label in labels):
            if len(set(labels)) != len(labels):
                return None
            rows = sorted(rows, key=lambda row: row[0])
        elif any(label is not None for label in labels):
            return None
        elif self._descending:
            rows = rows[::-1]
        z = [values for _, values in rows]
        x, y = _positions(corners, len(z[0]), len(z))
        return Mesh(z=z, format=fmt or "", x=x, y=y)


def _parse_row(text: str) -> tuple[int | None, list[float | None]] | None:
    """Split a row into its optional label and values; None for the column labels line."""
    cleaned = text.replace("[", " ").replace("]", " ")
    label: int | None = None
    match = _LABEL_RE.match(cleaned)
    rest = cleaned
    if match:
        label, rest = int(match.group(1)), match.group(2)
    values: list[float | None] = []
    for token in _TOKEN_RE.findall(rest):
        if _VALUE_RE.match(token):
            values.append(float(token))
        elif token.isdigit():
            return None
        else:
            values.append(None)
    return label, values


def _positions(corners: list[tuple[float, float]], cols: int, rows: int) -> tuple[list[float] | None, list[float] | None]:
    """Spread the grid over the mm extent the corner coordinates describe."""
    if len(corners) < 2:
        return None, None
    xs = [x for x, _ in corners]
    ys = [y for _, y in corners]
    x_min, x_max, y_min, y_max = min(xs), max(xs), min(ys), max(ys)
    if x_max <= x_min or y_max <= y_min:
        return None, None
    return spread(x_min, x_max, cols), spread(y_min, y_max, rows)


def spread(low: float, high: float, count: int) -> list[float]:
    """Evenly spaced positions from low to high, both included."""
    step = (high - low) / max(count - 1, 1)
    return [round(low + index * step, 3) for index in range(count)]
