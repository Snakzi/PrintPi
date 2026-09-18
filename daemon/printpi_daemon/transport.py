"""Open whatever the port URL points at and hand back a serial-like object.

Accepted forms:
  /dev/ttyUSB0                  local USB serial port (Linux)
  /dev/tty.usbmodem1234         local USB serial port (macOS)
  rfc2217://printer.local:3333  ser2net on the Pi, baud rate and DTR negotiated remotely
  socket://printer.local:3333   raw TCP bridge (socat), no reset on connect
  fake://?time_scale=1          simulated Marlin printer, see fake_printer.py
"""

from __future__ import annotations

import serial

from .fake_printer import FakePrinter


def open_port(url: str, baudrate: int, timeout: float):
    if url.startswith("fake://"):
        return FakePrinter.from_url(url)
    return serial.serial_for_url(url, baudrate=baudrate, timeout=timeout, write_timeout=timeout)
