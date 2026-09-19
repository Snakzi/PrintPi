"""Layer-by-layer timelapse of a print, taken from the camera.

The bridge opens a recording when a job starts, asks for a frame at every layer
change and closes it when the job ends; the first frame shows the empty bed and
the last one the finished part, taken once the end G-code has parked the head out
of the picture and before the job is reported as finished. Frames come from
ustreamer's snapshot endpoint or from any MJPEG stream URL (the first frame of the
multipart body) and are written as JPEG files under <root>/<job id>/. Closing
keeps the last frame as cover.jpg and assembles timelapse.gif with Pillow, plus
timelapse.mp4 when ffmpeg is on the PATH. The web app serves those files, so the
root defaults to its storage.
"""

from __future__ import annotations

import logging
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request
from pathlib import Path
from typing import Callable

log = logging.getLogger("printpi.timelapse")

FRAME_TIMEOUT = 5.0
# How long the job holds its end for the closing frame, so a camera that stopped answering
# cannot keep a finished print in "printing".
FINAL_FRAME_WAIT = FRAME_TIMEOUT
MAX_FRAME_BYTES = 8 << 20
MIN_INTERVAL = 2.0  # thin layers on a small part change faster than a camera is worth sampling
PENDING_GRABS = 2  # layer grabs queued behind a slow camera before further ones are dropped
MAX_GIF_FRAMES = 120
GIF_WIDTH = 480
GIF_FRAME_MS = 80
GIF_HOLD_MS = 1500
MP4_WIDTH = 720
MP4_FPS = 12

JPEG_START = b"\xff\xd8"
JPEG_END = b"\xff\xd9"

FrameFetcher = Callable[[str], bytes]


class TimelapseError(Exception):
    pass


def default_directory() -> str:
    """PRINTPI_TIMELAPSE_DIR, else the web app's storage in this checkout, else a temp dir."""
    configured = os.environ.get("PRINTPI_TIMELAPSE_DIR")
    if configured:
        return configured
    storage = Path(__file__).resolve().parents[2] / "app" / "storage" / "app"
    if storage.is_dir():
        return str(storage / "timelapse")
    return os.path.join(tempfile.gettempdir(), "printpi-timelapse")


def fetch_frame(url: str, timeout: float = FRAME_TIMEOUT) -> bytes:
    """One JPEG from a snapshot URL, or the first frame of an MJPEG stream."""
    request = urllib.request.Request(url, headers={"User-Agent": "printpi-daemon"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.headers.get_content_maintype() == "multipart":
                data = _first_frame(response, time.monotonic() + timeout)
            else:
                data = response.read(MAX_FRAME_BYTES)
    except (OSError, ValueError) as exc:  # URLError is an OSError
        raise TimelapseError(f"could not fetch {url}: {exc}") from exc
    if not data.startswith(JPEG_START):
        raise TimelapseError(f"{url} did not return a JPEG")
    return data


def _first_frame(stream, deadline: float) -> bytes:
    buffer = b""
    while time.monotonic() < deadline and len(buffer) < MAX_FRAME_BYTES:
        chunk = stream.read(16384)
        if not chunk:
            break
        buffer += chunk
        start = buffer.find(JPEG_START)
        if start < 0:
            buffer = buffer[-1:]  # a marker may straddle two chunks
            continue
        end = buffer.find(JPEG_END, start + 2)
        if end >= 0:
            return buffer[start:end + 2]
    raise TimelapseError("no complete frame in the stream")


class TimelapseRecorder:
    """Records one job at a time; capture() never blocks the caller."""

    def __init__(self, root: str | None = None, *, min_interval: float = MIN_INTERVAL,
                 fetch: FrameFetcher = fetch_frame) -> None:
        self.root = root or default_directory()
        self.min_interval = min_interval
        self._fetch = fetch
        self._lock = threading.Lock()
        self._recording: _Recording | None = None

    def begin(self, job_id: str, source: str | None) -> None:
        """Start recording from a snapshot or stream URL; None records nothing."""
        with self._lock:
            previous, self._recording = self._recording, None
        if previous is not None:
            previous.close()
        if not source:
            return
        recording = _Recording(os.path.join(self.root, job_id), source, self._fetch, self.min_interval)
        recording.request(force=True)
        with self._lock:
            self._recording = recording

    def capture(self) -> None:
        with self._lock:
            recording = self._recording
        if recording is not None:
            recording.request()

    def capture_final(self, timeout: float = FINAL_FRAME_WAIT) -> None:
        """The closing frame, taken now and waited for, so the finished part is on disk before the
        job ends and the record goes out."""
        with self._lock:
            recording = self._recording
        if recording is not None and recording.request(force=True, wait=timeout):
            recording.final_taken = True

    @property
    def recording(self) -> bool:
        return self._recording is not None

    @property
    def frames(self) -> int:
        """Frames written for the current recording."""
        recording = self._recording
        return recording.frames if recording is not None else 0

    def finish(self, *, gif: bool = True, mp4: bool = True) -> dict | None:
        """Take the closing frame unless capture_final() did, assemble the files asked for and report
        them; None when nothing was recorded."""
        with self._lock:
            recording, self._recording = self._recording, None
        if recording is None:
            return None
        if not recording.final_taken:
            recording.request(force=True)
        return recording.close(gif=gif, mp4=mp4)


class _Recording:
    def __init__(self, directory: str, source: str, fetch: FrameFetcher, min_interval: float) -> None:
        self.directory = directory
        self.source = source
        self._fetch = fetch
        self._min_interval = min_interval
        self._requests: queue.Queue[tuple[bool, threading.Event | None] | None] = queue.Queue()
        self._frames = 0
        self._last_capture = 0.0
        self._error: str | None = None
        self.final_taken = False
        self._thread = threading.Thread(target=self._run, name="timelapse", daemon=True)
        self._thread.start()

    @property
    def frames(self) -> int:
        return self._frames

    def request(self, force: bool = False, wait: float | None = None) -> bool:
        """Ask for a frame; with `wait` block until it is taken, at most that many seconds. A layer
        grab is dropped (False) while others are pending, since the layer will look the same; a
        forced one always queues, so the opening and closing frames are never lost."""
        if not force and self._requests.qsize() >= PENDING_GRABS:
            return False
        done = threading.Event() if wait is not None else None
        self._requests.put((force, done))
        if done is not None:
            done.wait(wait)
        return True

    def close(self, *, gif: bool = True, mp4: bool = True) -> dict:
        self._requests.put(None)
        self._thread.join(timeout=FRAME_TIMEOUT * 3)
        result = {"frames": self._frames, "gif": None, "mp4": None, "cover": None, "error": self._error}
        if self._frames == 0:
            shutil.rmtree(self.directory, ignore_errors=True)
            return result
        try:
            result.update(assemble(self.directory, gif=gif, mp4=mp4))
        except Exception as exc:  # noqa: BLE001 - the frames stay on disk for a retry by hand
            log.exception("could not assemble the timelapse in %s", self.directory)
            result["error"] = str(exc)
        return result

    def _run(self) -> None:
        while True:
            request = self._requests.get()
            if request is None:
                return
            force, done = request
            try:
                self._grab(force)
            finally:
                if done is not None:
                    done.set()

    def _grab(self, force: bool) -> None:
        now = time.monotonic()
        if not force and now - self._last_capture < self._min_interval:
            return
        try:
            data = self._fetch(self.source)
        except TimelapseError as exc:
            if self._error is None:
                log.warning("timelapse frame failed: %s", exc)
            self._error = str(exc)
            return
        os.makedirs(self.directory, exist_ok=True)
        self._frames += 1
        self._last_capture = now
        with open(os.path.join(self.directory, f"frame-{self._frames:05d}.jpg"), "wb") as handle:
            handle.write(data)


def frame_files(directory: str) -> list[str]:
    return sorted(
        os.path.join(directory, name) for name in os.listdir(directory) if name.startswith("frame-") and name.endswith(".jpg")
    )


def assemble(directory: str, *, gif: bool = True, mp4: bool = True) -> dict:
    """cover.jpg from the last frame, timelapse.gif with Pillow and timelapse.mp4 with ffmpeg as asked;
    the frames are removed once a movie exists, or right away when none was wanted."""
    frames = frame_files(directory)
    if not frames:
        return {"gif": None, "mp4": None, "cover": None}
    cover = os.path.join(directory, "cover.jpg")
    shutil.copyfile(frames[-1], cover)
    made_gif = made_mp4 = None
    if len(frames) >= 2:
        made_gif = _assemble_gif(directory, frames) if gif else None
        made_mp4 = _assemble_mp4(directory, frames) if mp4 else None
    if made_gif or made_mp4 or not (gif or mp4):
        for path in frames:
            os.remove(path)
    return {"gif": made_gif, "mp4": made_mp4, "cover": cover}


def _assemble_gif(directory: str, frames: list[str]) -> str | None:
    try:
        from PIL import Image
    except ImportError:
        log.warning("Pillow is not installed, keeping the frames in %s", directory)
        return None
    step = max(1, len(frames) / MAX_GIF_FRAMES)
    chosen = [frames[int(index * step)] for index in range(min(len(frames), MAX_GIF_FRAMES))]
    if chosen[-1] != frames[-1]:
        chosen.append(frames[-1])
    images = []
    for path in chosen:
        with Image.open(path) as frame:
            image = frame.convert("RGB")
        height = max(1, round(image.height * GIF_WIDTH / image.width))
        images.append(image.resize((GIF_WIDTH, height)).convert("P", palette=Image.Palette.ADAPTIVE, colors=128))
    target = os.path.join(directory, "timelapse.gif")
    durations = [GIF_FRAME_MS] * (len(images) - 1) + [GIF_HOLD_MS]
    images[0].save(target, save_all=True, append_images=images[1:], duration=durations, loop=0)
    return target


def _assemble_mp4(directory: str, frames: list[str]) -> str | None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return None
    target = os.path.join(directory, "timelapse.mp4")
    # A concat list keeps the numbering gaps of dropped frames from mattering.
    listing = os.path.join(directory, "frames.txt")
    with open(listing, "w", encoding="utf-8") as handle:
        for path in frames:
            handle.write(f"file '{os.path.basename(path)}'\n")
    command = [
        ffmpeg, "-y", "-loglevel", "error", "-r", str(MP4_FPS), "-f", "concat", "-safe", "0", "-i", listing,
        "-vf", f"scale={MP4_WIDTH}:-2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "23",
        target,
    ]
    try:
        subprocess.run(command, check=True, cwd=directory, capture_output=True, timeout=300)
    except (subprocess.SubprocessError, OSError) as exc:
        log.warning("ffmpeg failed: %s", getattr(exc, "stderr", b"").decode("utf-8", "replace").strip() or exc)
        return None
    finally:
        os.remove(listing)
    return target
