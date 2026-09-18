"""Webhook: every event the daemon raises, posted as JSON to one URL.

The body is {"event": "print_finished", "at": <unix seconds>, "payload": {...}} with the
event's payload as the plugins see it. A secret from the settings goes out as the
X-PrintPi-Secret header, so the receiver can tell the daemon from anyone else. Requests
run on their own thread one after the other, so a slow receiver never holds up the daemon;
the status keeps the last event, the last HTTP status and the last error for the plugin page.
With in_app on, the print events are also shown as notifications in the UI.
"""

from __future__ import annotations

import json
import queue
import threading
import time
import urllib.error
import urllib.request

from printpi_daemon.plugins import PluginBase, PluginError

TIMEOUT = 10.0
STOP_TIMEOUT = 3.0

NOTIFICATIONS = {
    "print_started": ("info", "Print started: {name}"),
    "print_finished": ("success", "Print finished: {name}"),
    "print_cancelled": ("warning", "Print cancelled: {name}"),
    "print_failed": ("error", "Print failed: {name}"),
}


class Plugin(PluginBase):
    _thread: threading.Thread | None = None

    def start(self) -> None:
        self._queue: queue.Queue[dict | None] = queue.Queue()
        self._sent = int(self.state.get("sent", 0))
        self._last: dict = dict(self.state.get("last") or {})
        self._thread = threading.Thread(target=self._work, name="webhook", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._thread is not None:
            self._queue.put(None)
            self._thread.join(timeout=STOP_TIMEOUT)
            self._thread = None

    def handle(self, action: str, value) -> None:
        if action != "test":
            raise PluginError(f"unknown action {action!r}")
        if not self._url():
            raise PluginError("set a URL first")
        self._queue.put({"event": "test", "at": time.time(), "payload": {"message": "Hello from PrintPi"}})

    def status(self) -> dict:
        return {"url_set": bool(self._url()), "sent": self._sent, **{f"last_{key}": value for key, value in self._last.items()}}

    def on_event(self, event: str, payload: dict) -> None:
        if self.settings.get("in_app") and event in NOTIFICATIONS:
            level, text = NOTIFICATIONS[event]
            self.notify(text.format(name=payload.get("name") or "print"), level)
        if self._url():
            self._queue.put({"event": event, "at": time.time(), "payload": payload})

    def _url(self) -> str:
        return str(self.settings.get("url") or "").strip()

    def _work(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                return
            self._post(item)

    def _post(self, item: dict) -> None:
        body = json.dumps(item).encode()
        headers = {"Content-Type": "application/json", "User-Agent": "PrintPi", "X-PrintPi-Event": item["event"]}
        secret = str(self.settings.get("secret") or "")
        if secret:
            headers["X-PrintPi-Secret"] = secret
        request = urllib.request.Request(self._url(), data=body, headers=headers, method="POST")
        result = {"event": item["event"], "at": item["at"], "status": None, "error": None}
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                result["status"] = response.status
        except urllib.error.HTTPError as exc:
            result["status"], result["error"] = exc.code, f"HTTP {exc.code}"
        except (urllib.error.URLError, OSError, ValueError) as exc:
            result["error"] = str(getattr(exc, "reason", exc))
        if result["error"] is None:
            self._sent += 1
        self._last = result
        self.state.update(sent=self._sent, last=result)
        self.save_state()
        self.status_changed()
