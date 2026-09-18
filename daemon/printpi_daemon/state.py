"""Snapshot of everything the daemon knows about the printer."""

from __future__ import annotations

import copy
import time
from dataclasses import asdict, dataclass, field


@dataclass
class Temperature:
    actual: float
    target: float | None = None


@dataclass
class PrinterState:
    port: str | None = None
    baudrate: int = 115200
    connection: str = "offline"  # offline | connecting | connected | error
    status: str = "idle"  # idle | busy | halted
    firmware: dict[str, str] = field(default_factory=dict)
    capabilities: dict[str, bool] = field(default_factory=dict)
    temperatures: dict[str, Temperature] = field(default_factory=dict)  # "T0", "B"
    position: dict[str, float] = field(default_factory=dict)
    last_error: str | None = None
    updated_at: float = field(default_factory=time.time)

    def snapshot(self) -> "PrinterState":
        return copy.deepcopy(self)

    def to_dict(self) -> dict:
        return asdict(self)
