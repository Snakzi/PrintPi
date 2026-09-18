"""Printer firmware updates: flash a file and follow the printer through its reboot.

FirmwareUpdater runs one flash at a time on its own thread and reports a status
dict the bridge writes to printpi:firmware. The methods, picked by the app from
the printer profile:

  buddy    Prusa Buddy boards (MK4/S, MK3.9, MK3.5, MINI, XL, CORE One) flash a .bbf
           that already lies on the printer's USB drive: "M997 /usb/<name>" reboots
           into the bootloader, which writes that file. Nothing can put the file on
           the drive from here: M28 is unimplemented in Buddy and PrusaLink's upload
           accepts G-code only, so the user copies it or sends it via Prusa Connect.
  avrdude  8-bit boards with a serial bootloader (Prusa MK3 family, older Creality
           boards): the port is released and avrdude writes the .hex through it.
  restart  32-bit Marlin boards flash firmware.bin from the SD card when they boot:
           "M997" restarts the board, then the new version is read back.

Every method ends with a reconnect that retries while the board boots, and the
status carries the firmware name before and after so the UI can show what changed.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import threading
import time
from typing import Callable

from .printer import Printer, PrinterError

log = logging.getLogger("printpi.firmware")

METHODS = ("buddy", "avrdude", "restart")
ACTIVE_PHASES = ("preparing", "flashing", "rebooting", "reconnecting")
LOG_LINES = 40
PROGRESS_BAR_WIDTH = 50  # avrdude draws its bars with fifty hashes

# A name as the file listing gives it; it must also be safe inside one G-code line.
_FILE_NAME_RE = re.compile(r"^[A-Za-z0-9._~+-]{1,64}$")
_MCU_RE = re.compile(r"^[a-z0-9]{1,32}$")
_PROGRAMMER_RE = re.compile(r"^[a-z0-9_-]{1,32}$")
_BAR_RE = re.compile(r"^(?P<stage>Reading|Writing)\s*\|\s*(?P<bar>#*)")
_STAGE_LINES = (
    ("reading input file", "Reading the file"),
    ("writing flash", "Writing flash"),
    ("verifying flash", "Verifying flash"),
    ("bytes of flash verified", "Flash verified"),
)


class FirmwareError(Exception):
    pass


def parse_file_list(lines: list[str]) -> list[dict]:
    """Files from an M20 reply.

    Marlin prints "NAME.GCO 12345" and with "M20 L" adds the long name in quotes;
    Buddy lists the root of the USB drive as bare 8.3 names, which are exactly what
    its M997 takes. Directories (a trailing slash in Marlin) are left out.
    """
    files: list[dict] = []
    inside = False
    for raw in lines:
        line = raw.strip()
        if line.startswith("Begin file list"):
            inside = True
            continue
        if line.startswith("End file list"):
            break
        if not inside or not line or line.startswith("echo:"):
            continue
        long_name = None
        if '"' in line:
            line, _, quoted = line.partition('"')
            long_name = quoted.rstrip('"').strip() or None
        parts = line.split()
        if not parts or parts[0].endswith("/"):
            continue
        size = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        files.append({"name": parts[0], "size": size, "long_name": long_name})
    return files


def list_files(printer: Printer) -> list[dict]:
    """The files on the printer's SD card or USB drive."""
    return parse_file_list(printer.send("M20", timeout=30))


def firmware_name(printer: Printer) -> str | None:
    name = printer.state.firmware.get("FIRMWARE_NAME")
    return name or None


class AvrdudeOutput:
    """Turns avrdude's output into log lines and progress.

    The progress bars are drawn in place ("Writing | ####      | 40%"), so the
    partial line is inspected as bytes arrive and only finished lines are logged.
    """

    def __init__(self, on_line: Callable[[str], None], on_progress: Callable[[str, float], None]) -> None:
        self._on_line = on_line
        self._on_progress = on_progress
        self._buffer = ""
        self._verifying = False

    def feed(self, data: bytes) -> None:
        self._buffer += data.decode("utf-8", errors="replace")
        while True:
            index = min((i for i in (self._buffer.find("\n"), self._buffer.find("\r")) if i >= 0), default=-1)
            if index < 0:
                break
            line, self._buffer = self._buffer[:index], self._buffer[index + 1:]
            self._line(line.strip(), final=True)
        if self._buffer.strip():
            self._line(self._buffer.strip(), final=False)

    def _line(self, line: str, *, final: bool) -> None:
        if not line:
            return
        lowered = line.lower()
        for needle, stage in _STAGE_LINES:
            if needle in lowered:
                self._verifying = stage == "Verifying flash"
                self._on_progress(stage, 0.0)
        bar = _BAR_RE.match(line)
        if bar is not None:
            stage = "Writing flash" if bar.group("stage") == "Writing" else (
                "Verifying flash" if self._verifying else "Reading flash")
            self._on_progress(stage, min(1.0, len(bar.group("bar")) / PROGRESS_BAR_WIDTH))
        if final:
            self._on_line(line)

    def close(self) -> None:
        if self._buffer.strip():
            self._on_line(self._buffer.strip())
        self._buffer = ""


class FirmwareUpdater:
    def __init__(
        self,
        *,
        printer: Callable[[], Printer],
        connect: Callable[[], None],
        disconnect: Callable[[], None],
        on_status: Callable[[dict], None] | None = None,
        run: Callable[..., subprocess.Popen] = subprocess.Popen,
        port_exists: Callable[[str], bool] = os.path.exists,
        which: Callable[[str], str | None] = shutil.which,
        sleep: Callable[[float], None] = time.sleep,
        vanish_timeout: float = 20.0,
        reboot_timeout: float = 600.0,
        reconnect_timeout: float = 180.0,
        retry_interval: float = 5.0,
        settle: float = 2.0,
    ) -> None:
        # Looked up per call: a reconnect may replace the bridge's printer object.
        self._printer = printer
        self._connect = connect
        self._disconnect = disconnect
        self._on_status = on_status
        self._run = run
        self._port_exists = port_exists
        self._which = which
        self._sleep = sleep
        self.vanish_timeout = vanish_timeout
        self.reboot_timeout = reboot_timeout
        self.reconnect_timeout = reconnect_timeout
        self.retry_interval = retry_interval
        self.settle = settle
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._status: dict = self._idle()

    def _idle(self) -> dict:
        return {
            "phase": "idle", "method": None, "file": None, "step": None, "progress": None, "log": [],
            "error": None, "started_at": None, "finished_at": None, "firmware_before": None, "firmware_after": None,
        }

    def status(self) -> dict:
        with self._lock:
            status = dict(self._status)
            status["log"] = list(status["log"])
        status["avrdude_available"] = self._which("avrdude") is not None
        return status

    @property
    def active(self) -> bool:
        return self._status["phase"] in ACTIVE_PHASES

    def start(self, method: str, *, file: str | None = None, port: str | None = None, mcu: str | None = None,
              programmer: str | None = None, baud: int | None = None) -> dict:
        """Validate the request and flash on a thread; raises FirmwareError when it cannot start."""
        if method not in METHODS:
            raise FirmwareError(f"unknown firmware method {method!r}")
        with self._lock:
            if self.active:
                raise FirmwareError("a firmware update is already running")
            printer = self._printer()
            if method in ("buddy", "restart"):
                if not printer.connected:
                    raise FirmwareError("the printer is not connected")
                if method == "buddy":
                    if not file or not _FILE_NAME_RE.match(file):
                        raise FirmwareError("a firmware file on the printer's USB drive is required")
                    if not file.lower().endswith(".bbf"):
                        raise FirmwareError("Buddy firmware files end with .bbf")
                options: dict = {"command": f"M997 /usb/{file}" if method == "buddy" else "M997"}
            else:
                if not file or not os.path.isfile(file):
                    raise FirmwareError("the firmware file does not exist")
                port = port or printer.port_url
                if not port.startswith("/dev/"):
                    raise FirmwareError(f"avrdude needs a local serial port, not {port or 'none'}")
                mcu, programmer = (mcu or "atmega2560").lower(), (programmer or "wiring").lower()
                if not _MCU_RE.match(mcu) or not _PROGRAMMER_RE.match(programmer):
                    raise FirmwareError("invalid avrdude parameters")
                options = {"path": file, "port": port, "mcu": mcu, "programmer": programmer, "baud": int(baud or 115200)}
            self._status = self._idle() | {
                "phase": "preparing", "method": method, "file": os.path.basename(file) if file else None,
                "started_at": time.time(), "firmware_before": firmware_name(printer),
            }
            self._thread = threading.Thread(target=self._flash, args=(method, options), name="firmware-flash", daemon=True)
        status = self.status()
        self._changed()
        self._thread.start()
        return status

    # ---- the flash itself ---------------------------------------------------------

    def _flash(self, method: str, options: dict) -> None:
        try:
            if method == "avrdude":
                self._flash_with_avrdude(**options)
            else:
                self._flash_by_reboot(options["command"])
            self._reconnect()
            after = firmware_name(self._printer())
            self._log(f"firmware now reports {after or 'nothing'}")
            self._set(phase="done", step=None, progress=None, finished_at=time.time(), firmware_after=after)
            log.info("firmware update finished: %s", after)
        except FirmwareError as exc:
            log.warning("firmware update failed: %s", exc)
            self._set(phase="failed", error=str(exc), progress=None, finished_at=time.time())
        except Exception as exc:  # noqa: BLE001 - the status must always end
            log.exception("firmware update crashed")
            self._set(phase="failed", error=f"{type(exc).__name__}: {exc}", progress=None, finished_at=time.time())

    def _flash_by_reboot(self, command: str) -> None:
        printer = self._printer()
        port = printer.port_url
        self._set(phase="flashing", step=f"Sending {command}")
        self._log(f"> {command}")
        try:
            printer.send(command, timeout=15)
        except PrinterError as exc:
            # Boards that reset right after the ok may close the port before it is read.
            self._log(f"the port closed right after {command}: {exc}")
        self._set(phase="rebooting", step="Waiting for the printer to restart", progress=None)
        if port.startswith("/dev/"):
            if self._wait(lambda: not self._port_exists(port), self.vanish_timeout):
                self._log(f"{port} is gone, the board is rebooting")
                self._set(step="Waiting for the printer to come back")
                if not self._wait(lambda: self._port_exists(port), self.reboot_timeout):
                    raise FirmwareError(f"{port} did not come back within {int(self.reboot_timeout)} s")
                self._log(f"{port} is back")
            else:
                self._log(f"{port} did not go away, the board may not have restarted")
        else:
            self._sleep(self.settle)
        if printer.connected:
            self._disconnect()

    def _flash_with_avrdude(self, path: str, port: str, mcu: str, programmer: str, baud: int) -> None:
        tool = self._which("avrdude")
        if tool is None:
            raise FirmwareError("avrdude is not installed on this host")
        ext = path.rsplit(".", 1)[-1].lower() if "." in os.path.basename(path) else ""
        fmt = {"hex": "i", "bin": "r"}.get(ext, "a")
        args = [tool, "-p", mcu, "-c", programmer, "-P", port, "-b", str(baud), "-D", "-U", f"flash:w:{path}:{fmt}"]
        if self._printer().connected:
            self._set(phase="preparing", step="Releasing the serial port")
            self._disconnect()
            self._sleep(self.settle)
        self._set(phase="flashing", step="Starting avrdude", progress=None)
        self._log("$ " + " ".join(args))
        try:
            process = self._run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
        except OSError as exc:
            raise FirmwareError(f"could not start avrdude: {exc}") from exc
        output = AvrdudeOutput(on_line=self._log, on_progress=lambda stage, value: self._set(step=stage, progress=value))
        stream = process.stdout
        assert stream is not None
        try:
            while chunk := stream.read(1024):
                output.feed(chunk)
        finally:
            output.close()
            stream.close()
        code = process.wait()
        if code != 0:
            last = next((line for line in reversed(self.status()["log"]) if not line.startswith("$")), "")
            raise FirmwareError(f"avrdude exited with status {code}" + (f": {last}" if last else ""))
        self._set(phase="rebooting", step="Waiting for the board to restart", progress=None)
        self._sleep(self.settle)

    def _reconnect(self) -> None:
        self._set(phase="reconnecting", step="Reconnecting", progress=None)
        deadline = time.monotonic() + self.reconnect_timeout
        while True:
            try:
                self._connect()
            except PrinterError as exc:
                self._log(f"connect failed: {exc}")
                if time.monotonic() >= deadline:
                    raise FirmwareError(f"the printer did not answer within {int(self.reconnect_timeout)} s: {exc}") from exc
                self._sleep(self.retry_interval)
                continue
            if self._printer().connected:
                return
            if time.monotonic() >= deadline:
                raise FirmwareError(f"the printer did not answer within {int(self.reconnect_timeout)} s")
            self._sleep(self.retry_interval)

    def _wait(self, predicate: Callable[[], bool], timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while not predicate():
            if time.monotonic() >= deadline:
                return False
            self._sleep(0.5)
        return True

    # ---- status -------------------------------------------------------------------

    def _set(self, **fields) -> None:
        with self._lock:
            self._status.update(fields)
        self._changed()

    def _log(self, line: str) -> None:
        with self._lock:
            self._status["log"] = (self._status["log"] + [line])[-LOG_LINES:]
        self._changed()

    def _changed(self) -> None:
        if self._on_status is None:
            return
        try:
            self._on_status(self.status())
        except Exception:  # noqa: BLE001 - reporting must not break the flash
            log.exception("firmware status listener failed")
