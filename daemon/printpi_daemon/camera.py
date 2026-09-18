"""USB cameras: discovery through V4L2 and an MJPEG stream through ustreamer.

Discovery reads /sys/class/video4linux and asks each node for its capabilities,
keeping only USB devices that capture video (a webcam also exposes a metadata
node, and the Pi has a dozen codec/ISP nodes that are not cameras). Streaming
spawns ustreamer bound to localhost; nginx on the Pi proxies it under /webcam/.
"""

from __future__ import annotations

import logging
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time

log = logging.getLogger("printpi.camera")

SYS_V4L = "/sys/class/video4linux"
VIDIOC_QUERYCAP = 0x80685600  # _IOR('V', 0, struct v4l2_capability[104 bytes])
CAP_VIDEO_CAPTURE = 0x00000001
CAP_META_CAPTURE = 0x00800000


class CameraError(Exception):
    pass


def list_cameras() -> list[dict[str, str]]:
    """USB video capture devices, one entry per physical camera."""
    if sys.platform != "linux" or not os.path.isdir(SYS_V4L):
        return []
    cameras: list[dict[str, str]] = []
    seen: set[str] = set()
    for entry in sorted(os.listdir(SYS_V4L), key=_node_index):
        node = f"/dev/{entry}"
        info = _query_capability(node)
        if info is None:
            continue
        driver, card, bus, device_caps = info
        if not bus.startswith("usb"):
            continue
        if not device_caps & CAP_VIDEO_CAPTURE or device_caps & CAP_META_CAPTURE:
            continue
        if bus in seen:
            continue
        seen.add(bus)
        cameras.append({"device": node, "name": card, "bus": bus, "driver": driver})
    return cameras


def _node_index(name: str) -> int:
    digits = "".join(ch for ch in name if ch.isdigit())
    return int(digits) if digits else 0


def _query_capability(node: str) -> tuple[str, str, str, int] | None:
    import fcntl  # Linux only, imported here so the module loads everywhere

    try:
        fd = os.open(node, os.O_RDWR | os.O_NONBLOCK)
    except OSError:
        return None
    try:
        buffer = bytearray(104)
        fcntl.ioctl(fd, VIDIOC_QUERYCAP, buffer)
    except OSError:
        return None
    finally:
        os.close(fd)
    driver = _cstring(buffer[0:16])
    card = _cstring(buffer[16:48])
    bus = _cstring(buffer[48:80])
    _version, _capabilities, device_caps = struct.unpack("=III", buffer[80:92])
    return driver, card, bus, device_caps


def _cstring(raw: bytes | bytearray) -> str:
    return bytes(raw).split(b"\0", 1)[0].decode("utf-8", errors="replace")


class CameraStreamer:
    """Runs one ustreamer process for the selected camera."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080) -> None:
        self.host = host
        self.port = port
        self._lock = threading.Lock()
        self._process: subprocess.Popen | None = None
        self._device: str | None = None
        self._error: str | None = None

    @staticmethod
    def available() -> bool:
        return shutil.which("ustreamer") is not None

    def start(self, device: str, resolution: str = "1280x720", fps: int = 15) -> None:
        with self._lock:
            if not self.available():
                raise CameraError("ustreamer is not installed")
            if not os.path.exists(device):
                raise CameraError(f"{device} does not exist")
            self._stop_locked()
            # Prefer the camera's own MJPEG stream, fall back to whatever it offers.
            for pixel_format in ("MJPEG", None):
                command = [
                    "ustreamer", "--device", device, "--host", self.host, "--port", str(self.port),
                    "--resolution", resolution, "--desired-fps", str(fps), "--drop-same-frames", "30",
                ]
                if pixel_format:
                    command += ["--format", pixel_format]
                stderr = tempfile.TemporaryFile()
                process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=stderr)
                time.sleep(1.0)
                if process.poll() is None:
                    self._process, self._device, self._error = process, device, None
                    log.info("ustreamer serving %s on %s:%d", device, self.host, self.port)
                    return
                stderr.seek(0)
                tail = stderr.read().decode("utf-8", errors="replace").strip().splitlines()
                self._error = tail[-1] if tail else f"ustreamer exited with {process.returncode}"
                log.warning("ustreamer failed on %s (%s): %s", device, pixel_format or "default", self._error)
            raise CameraError(f"could not start ustreamer on {device}: {self._error}")

    def stop(self) -> None:
        with self._lock:
            self._stop_locked()

    def _stop_locked(self) -> None:
        process, self._process, self._device = self._process, None, None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()

    def snapshot_url(self) -> str | None:
        """Where a single JPEG can be fetched while the stream runs."""
        return f"http://{self.host}:{self.port}/snapshot" if self.status()["running"] else None

    def status(self) -> dict:
        with self._lock:
            process = self._process
            running = process is not None and process.poll() is None
            if process is not None and not running:
                self._error = f"ustreamer exited with {process.returncode}"
                self._process, self._device = None, None
            return {
                "running": running,
                "device": self._device if running else None,
                "port": self.port,
                "available": self.available(),
                "error": self._error,
            }
