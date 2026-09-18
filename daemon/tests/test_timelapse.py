"""Timelapse frames from snapshot and MJPEG sources, the recorder and the assembly."""

import http.server
import io
import os
import threading
import time

import pytest
from PIL import Image

from printpi_daemon.timelapse import TimelapseError, TimelapseRecorder, assemble, fetch_frame, frame_files


def jpeg(color=(200, 40, 40), size=(64, 48)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="JPEG")
    return buffer.getvalue()


def wait_for(predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


class CameraHandler(http.server.BaseHTTPRequestHandler):
    frame = jpeg()

    def do_GET(self):  # noqa: N802 - http.server API
        if self.path == "/snapshot":
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(self.frame)))
            self.end_headers()
            self.wfile.write(self.frame)
        elif self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            for _ in range(2):
                self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(self.frame))
                self.wfile.write(self.frame)
                self.wfile.write(b"\r\n")
        elif self.path == "/page":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html>not a camera</html>")
        else:
            self.send_error(404)

    def log_message(self, *args):  # quiet
        pass


@pytest.fixture(scope="module")
def camera():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), CameraHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def counting_fetch(calls: list[str]):
    def fetch(url: str) -> bytes:
        calls.append(url)
        return jpeg(((len(calls) * 50) % 256, 90, 30))

    return fetch


def test_fetch_frame_from_a_snapshot_url(camera):
    assert fetch_frame(f"{camera}/snapshot") == CameraHandler.frame


def test_fetch_frame_takes_the_first_frame_of_an_mjpeg_stream(camera):
    assert fetch_frame(f"{camera}/stream") == CameraHandler.frame


def test_fetch_frame_rejects_other_content_and_dead_hosts(camera):
    with pytest.raises(TimelapseError, match="did not return a JPEG"):
        fetch_frame(f"{camera}/page")
    with pytest.raises(TimelapseError, match="could not fetch"):
        fetch_frame(f"{camera}/missing")
    with pytest.raises(TimelapseError, match="could not fetch"):
        fetch_frame("http://127.0.0.1:1/snapshot", timeout=1.0)


def test_recording_takes_the_opening_layer_and_closing_frames(tmp_path):
    calls: list[str] = []
    recorder = TimelapseRecorder(str(tmp_path), min_interval=0, fetch=counting_fetch(calls))
    assert recorder.finish() is None

    recorder.begin("job1", "http://cam/snapshot")
    assert recorder.recording
    assert wait_for(lambda: recorder.frames == 1)
    for expected in (2, 3, 4):
        recorder.capture()
        assert wait_for(lambda: recorder.frames == expected)

    result = recorder.finish()
    assert not recorder.recording
    assert result["frames"] == 5 and result["error"] is None
    assert calls == ["http://cam/snapshot"] * 5
    directory = tmp_path / "job1"
    assert result["gif"] == str(directory / "timelapse.gif") and os.path.isfile(result["gif"])
    assert result["cover"] == str(directory / "cover.jpg") and os.path.isfile(result["cover"])
    assert frame_files(str(directory)) == []
    with Image.open(result["gif"]) as gif:
        assert gif.n_frames == 5
        assert gif.width == 480
    assert result["mp4"] is None or os.path.isfile(result["mp4"])


def test_layer_frames_are_rate_limited_but_the_closing_frame_is_not(tmp_path):
    recorder = TimelapseRecorder(str(tmp_path), min_interval=60, fetch=counting_fetch([]))
    recorder.begin("job2", "http://cam/snapshot")
    assert wait_for(lambda: recorder.frames == 1)
    recorder.capture()
    recorder.capture()
    time.sleep(0.05)
    assert recorder.finish()["frames"] == 2


def test_without_a_source_nothing_is_recorded(tmp_path):
    recorder = TimelapseRecorder(str(tmp_path), fetch=counting_fetch([]))
    recorder.begin("job3", None)
    assert not recorder.recording
    recorder.capture()
    assert recorder.finish() is None
    assert not (tmp_path / "job3").exists()


def test_a_camera_that_answers_nothing_leaves_no_files(tmp_path):
    def failing(url: str) -> bytes:
        raise TimelapseError("connection refused")

    recorder = TimelapseRecorder(str(tmp_path), min_interval=0, fetch=failing)
    recorder.begin("job4", "http://cam/snapshot")
    recorder.capture()
    result = recorder.finish()
    assert result["frames"] == 0 and result["gif"] is None and result["cover"] is None
    assert result["error"] == "connection refused"
    assert not (tmp_path / "job4").exists()


def test_assemble_keeps_a_single_frame_as_cover_only(tmp_path):
    directory = tmp_path / "single"
    directory.mkdir()
    (directory / "frame-00001.jpg").write_bytes(jpeg())
    result = assemble(str(directory))
    assert result["gif"] is None and result["cover"] == str(directory / "cover.jpg")
    assert frame_files(str(directory)) == [str(directory / "frame-00001.jpg")]


def test_the_final_frame_is_waited_for_and_not_taken_twice(tmp_path):
    calls: list[str] = []
    recorder = TimelapseRecorder(str(tmp_path), min_interval=60, fetch=counting_fetch(calls))
    recorder.begin("job3", "http://cam/snapshot")
    assert wait_for(lambda: recorder.frames == 1)
    recorder.capture_final()
    assert recorder.frames == 2  # on disk before the call returned
    result = recorder.finish()
    assert result["frames"] == 2 and len(calls) == 2
    assert os.path.isfile(result["cover"])


def test_assemble_makes_only_the_files_asked_for(tmp_path):
    def frames_in(name: str) -> str:
        directory = tmp_path / name
        directory.mkdir()
        for index in (1, 2):
            (directory / f"frame-0000{index}.jpg").write_bytes(jpeg())
        return str(directory)

    gif_only = assemble(frames_in("gif"), mp4=False)
    assert gif_only["gif"] and gif_only["mp4"] is None and gif_only["cover"]
    assert frame_files(gif_only["cover"].rsplit("/", 1)[0]) == []

    nothing = assemble(frames_in("none"), gif=False, mp4=False)
    assert nothing["gif"] is None and nothing["mp4"] is None and nothing["cover"]
    assert frame_files(nothing["cover"].rsplit("/", 1)[0]) == []  # frames are dropped, the cover stays
