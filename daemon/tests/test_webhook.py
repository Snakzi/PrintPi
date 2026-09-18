"""The built-in webhook plugin against a local HTTP server."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from printpi_daemon.plugins import PluginError, PluginHost

PLUGIN_PATH = Path(__file__).resolve().parents[2] / "plugins" / "webhook"
PLUGIN_ID = "webhook"


class Receiver:
    def __init__(self, status: int = 200) -> None:
        self.requests: list[tuple[dict, dict]] = []
        received = self.requests

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                received.append(({key.lower(): value for key, value in self.headers.items()}, json.loads(body)))
                self.send_response(status)
                self.end_headers()

            def log_message(self, *args) -> None:
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/hook"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()


def wait_for(condition, timeout: float = 3.0):
    deadline = time.monotonic() + timeout
    while True:
        result = condition()
        if result:
            return result
        if time.monotonic() > deadline:
            raise AssertionError("condition not met in time")
        time.sleep(0.02)


def spec(**settings) -> dict:
    return {"id": PLUGIN_ID, "path": str(PLUGIN_PATH), "version": "1.0.0", "settings": settings}


@pytest.fixture
def saved() -> dict:
    return {}


@pytest.fixture
def host(saved):
    notes: list = []
    h = PluginHost(load_state=lambda plugin_id: saved.get(plugin_id, {}), save_state=saved.__setitem__,
                   notify=lambda plugin_id, level, message, title: notes.append((level, message)))
    h.notes = notes
    yield h
    h.stop_all()


def status(host: PluginHost) -> dict:
    return host.statuses()[PLUGIN_ID]["status"]


def test_manifest_matches_the_plugin():
    manifest = json.loads((PLUGIN_PATH / "plugin.json").read_text())
    assert manifest["id"] == PLUGIN_ID
    assert {field["key"] for field in manifest["settings"]} == {"url", "secret", "in_app"}
    (control,) = manifest["controls"]
    assert control["type"] == "button" and control["action"] == "test"


def test_events_are_posted_with_the_secret(host, saved):
    receiver = Receiver()
    try:
        host.sync([spec(url=receiver.url, secret="s3cret")])
        assert status(host) == {"url_set": True, "sent": 0}
        host.notify_event("print_finished", {"name": "cube.gcode", "progress": 1.0})
        headers, body = wait_for(lambda: receiver.requests and receiver.requests[0])
        assert body["event"] == "print_finished" and body["payload"]["name"] == "cube.gcode" and body["at"] > 0
        assert headers["x-printpi-secret"] == "s3cret" and headers["x-printpi-event"] == "print_finished"
        assert headers["content-type"] == "application/json"
        wait_for(lambda: status(host)["sent"] == 1)
        assert status(host)["last_status"] == 200 and status(host)["last_error"] is None
        assert saved[PLUGIN_ID]["sent"] == 1
    finally:
        receiver.close()
    assert host.notes == []


def test_failures_are_reported_and_the_test_button_needs_a_url(host):
    receiver = Receiver(status=500)
    try:
        host.sync([spec(url=receiver.url)])
        host.action(PLUGIN_ID, "test")
        wait_for(lambda: status(host).get("last_status") == 500)
        assert status(host)["last_error"] == "HTTP 500" and status(host)["sent"] == 0
        assert receiver.requests[0][1] == {"event": "test", "at": receiver.requests[0][1]["at"], "payload": {"message": "Hello from PrintPi"}}
        assert "x-printpi-secret" not in receiver.requests[0][0]
    finally:
        receiver.close()
    host.sync([spec(url="http://127.0.0.1:9/nobody")])
    host.notify_event("connected", {"port": "/dev/ttyACM0"})
    wait_for(lambda: status(host).get("last_event") == "connected")
    assert status(host)["last_status"] is None and status(host)["last_error"]
    host.sync([spec(url="")])
    with pytest.raises(PluginError, match="URL"):
        host.action(PLUGIN_ID, "test")


def test_print_events_become_notifications_when_asked(host):
    host.sync([spec(url="", in_app=True)])
    host.notify_event("print_started", {"name": "cube.gcode"})
    host.notify_event("layer_changed", {"name": "cube.gcode", "layer": 2})
    host.notify_event("print_failed", {"name": None})
    assert host.notes == [("info", "Print started: cube.gcode"), ("error", "Print failed: print")]
