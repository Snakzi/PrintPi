import os
import stat
import sys

import pytest

from printpi_daemon.camera import CameraError, CameraStreamer, list_cameras


def fake_ustreamer(tmp_path, script: str) -> str:
    """Put a fake ustreamer executable first on PATH and return the directory."""
    binary = tmp_path / "bin" / "ustreamer"
    binary.parent.mkdir(exist_ok=True)
    binary.write_text("#!/bin/sh\n" + script + "\n")
    binary.chmod(binary.stat().st_mode | stat.S_IEXEC)
    return str(binary.parent)


@pytest.fixture
def path(tmp_path, monkeypatch):
    def use(script: str) -> None:
        monkeypatch.setenv("PATH", fake_ustreamer(tmp_path, script) + os.pathsep + os.environ.get("PATH", ""))

    return use


@pytest.fixture
def device(tmp_path) -> str:
    node = tmp_path / "video0"
    node.write_text("")
    return str(node)


def test_list_cameras_is_empty_where_there_is_no_v4l2():
    if sys.platform == "linux" and os.path.isdir("/sys/class/video4linux"):
        pytest.skip("real V4L2 present")
    assert list_cameras() == []


def test_start_without_ustreamer_raises(monkeypatch, tmp_path, device):
    monkeypatch.setenv("PATH", str(tmp_path))
    streamer = CameraStreamer()
    assert streamer.available() is False
    with pytest.raises(CameraError, match="not installed"):
        streamer.start(device)


def test_start_status_stop(path, device):
    path("exec sleep 30")
    streamer = CameraStreamer(port=18080)
    streamer.start(device)
    status = streamer.status()
    assert status["running"] is True
    assert status["device"] == device
    assert status["port"] == 18080
    assert status["error"] is None
    streamer.stop()
    assert streamer.status()["running"] is False


def test_missing_device_raises(path, tmp_path):
    path("exec sleep 30")
    with pytest.raises(CameraError, match="does not exist"):
        CameraStreamer().start(str(tmp_path / "nope"))


def test_failing_streamer_reports_last_stderr_line(path, device):
    path('echo "-- Can not open device" >&2; exit 1')
    streamer = CameraStreamer()
    with pytest.raises(CameraError, match="Can not open device"):
        streamer.start(device)
    assert streamer.status()["running"] is False
    assert "Can not open device" in streamer.status()["error"]


def test_bridge_camera_commands(path, device):
    from printpi_daemon.bridge import EVENTS_CHANNEL, RedisBridge
    from printpi_daemon.printer import Printer

    path("exec sleep 30")
    bridge = RedisBridge("redis://127.0.0.1:1/0", Printer("fake://?time_scale=0.01"))
    bridge._remember_camera = lambda device: None  # no redis in tests
    try:
        bridge._execute({"type": "camera_start", "device": device})
        assert bridge.camera.status()["running"] is True
        bridge._execute({"type": "camera_stop"})
        assert bridge.camera.status()["running"] is False
        bridge._execute({"type": "camera_start", "device": "/nonexistent"})
        events = []
        while not bridge._outbox.empty():
            channel, payload = bridge._outbox.get_nowait()
            if channel == EVENTS_CHANNEL:
                events.append(payload)
        assert '"camera_started"' in events[0]
        assert '"camera_stopped"' in events[1]
        assert '"error"' in events[2]
    finally:
        bridge.camera.stop()
