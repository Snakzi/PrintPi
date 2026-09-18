"""Line-by-line log of everything sent to and received from the printer.

This is the single most useful debugging artefact: when something goes wrong,
the serial log shows exactly what the firmware saw and answered, with timestamps.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime

log = logging.getLogger("printpi.serial")


class SerialLog:
    def __init__(self, path: str | None = None) -> None:
        self._file = open(path, "a", buffering=1, encoding="utf-8") if path else None
        self._lock = threading.Lock()

    def tx(self, line: str) -> None:
        self._write("TX", line)

    def rx(self, line: str) -> None:
        self._write("RX", line)

    def event(self, text: str) -> None:
        self._write("--", text)

    def close(self) -> None:
        with self._lock:
            if self._file:
                self._file.close()
                self._file = None

    def _write(self, tag: str, text: str) -> None:
        log.debug("%s %s", tag, text)
        if self._file is None:
            return
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with self._lock:
            if self._file:
                self._file.write(f"{stamp} {tag} {text}\n")
