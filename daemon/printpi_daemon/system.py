"""Host statistics for the dashboard: load, memory, disk, CPU temperature, uptime.

Everything is read from /proc and /sys so no extra package is needed on the Pi.
Values that the host cannot provide (a Mac has no /proc) are reported as None.
SystemMonitor adds the CPU utilisation between two samples and folds the samples
into the usage history the settings page charts.
"""

from __future__ import annotations

import functools
import os
import shutil
import socket
import subprocess
import sys
import time
from typing import Callable

HISTORY_INTERVAL = 30.0  # seconds per history point
HISTORY_SIZE = 2880  # 24 h of points


# vcgencmd get_throttled: the low nibble is the state now, bits 16-19 whether it happened since boot.
THROTTLE_FLAGS = {
    "under_voltage": 1 << 0,
    "frequency_capped": 1 << 1,
    "throttled": 1 << 2,
    "temperature_limit": 1 << 3,
    "under_voltage_occurred": 1 << 16,
    "frequency_capped_occurred": 1 << 17,
    "throttled_occurred": 1 << 18,
    "temperature_limit_occurred": 1 << 19,
}


def system_stats() -> dict:
    return {
        "hostname": socket.gethostname(),
        "platform": sys.platform,
        "cpu_count": os.cpu_count(),
        "load": _load(),
        "uptime_seconds": _uptime(),
        "cpu_temperature": _cpu_temperature(),
        "memory": _memory(),
        "disk": _disk(),
        "throttled": _throttled(),
        "ip": _ip_address(),
        "sampled_at": time.time(),
        **host_facts(),
    }


@functools.lru_cache(maxsize=1)
def host_facts() -> dict:
    """What does not change while the daemon runs: board model, OS release, kernel, architecture."""
    uname = os.uname()
    return {
        "model": _read_text("/proc/device-tree/model"),
        "os": _os_release_name(),
        "kernel": uname.release,
        "arch": uname.machine,
    }


def _read_text(path: str) -> str | None:
    try:
        with open(path, "rb") as handle:
            return handle.read().replace(b"\0", b"").decode("utf-8", "replace").strip() or None
    except OSError:
        return None


def _os_release_name() -> str | None:
    try:
        with open("/etc/os-release", encoding="utf-8") as handle:
            for line in handle:
                key, _, value = line.strip().partition("=")
                if key == "PRETTY_NAME":
                    return value.strip('"') or None
    except OSError:
        pass
    if sys.platform == "darwin":
        return "macOS"
    return None


def _ip_address() -> str | None:
    """The address the host would use to reach the LAN, without sending anything."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("10.255.255.255", 1))
            return probe.getsockname()[0]
    except OSError:
        return None


def parse_throttled(value: str) -> dict | None:
    """The flags of a ``throttled=0x80008`` line (or a bare hex number) as booleans."""
    _, _, number = value.strip().rpartition("=")
    try:
        bits = int(number, 16)
    except ValueError:
        return None
    return {"raw": f"0x{bits:x}", **{name: bool(bits & mask) for name, mask in THROTTLE_FLAGS.items()}}


def _throttled() -> dict | None:
    """Under-voltage and thermal throttling from the Pi firmware; None on any other host."""
    vcgencmd = shutil.which("vcgencmd")
    if vcgencmd is None:
        return None
    try:
        output = subprocess.run([vcgencmd, "get_throttled"], capture_output=True, text=True, timeout=2, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return parse_throttled(output)


def _load() -> list[float] | None:
    try:
        return [round(value, 2) for value in os.getloadavg()]
    except (OSError, AttributeError):
        return None


def _uptime() -> float | None:
    try:
        with open("/proc/uptime", encoding="ascii") as handle:
            return float(handle.read().split()[0])
    except (OSError, ValueError, IndexError):
        return None


def _cpu_temperature() -> float | None:
    for path in ("/sys/class/thermal/thermal_zone0/temp", "/sys/class/hwmon/hwmon0/temp1_input"):
        try:
            with open(path, encoding="ascii") as handle:
                return round(int(handle.read().strip()) / 1000, 1)
        except (OSError, ValueError):
            continue
    return None


def _memory() -> dict | None:
    try:
        fields: dict[str, int] = {}
        with open("/proc/meminfo", encoding="ascii") as handle:
            for line in handle:
                key, _, rest = line.partition(":")
                fields[key] = int(rest.split()[0]) * 1024  # kB -> bytes
        total = fields["MemTotal"]
        available = fields.get("MemAvailable", fields.get("MemFree", 0))
    except (OSError, KeyError, ValueError, IndexError):
        return None
    return {
        "total": total,
        "available": available,
        "used_percent": round((total - available) / total * 100, 1) if total else None,
    }


def _disk(path: str = "/") -> dict | None:
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return None
    return {
        "total": usage.total,
        "free": usage.free,
        "used_percent": round((usage.total - usage.free) / usage.total * 100, 1) if usage.total else None,
    }


def _cpu_times() -> tuple[int, int] | None:
    """(idle, total) jiffies from the first line of /proc/stat, None where there is no /proc."""
    try:
        with open("/proc/stat", encoding="ascii") as handle:
            fields = handle.readline().split()
    except OSError:
        return None
    if len(fields) < 5 or fields[0] != "cpu":
        return None
    try:
        values = [int(field) for field in fields[1:9]]  # user nice system idle iowait irq softirq steal
    except ValueError:
        return None
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    return idle, sum(values)


class SystemMonitor:
    """Samples the host with every heartbeat and folds the samples into one history point per interval.

    A point is ``[unix seconds at the start of the interval, cpu %, memory %]`` with the mean over
    the interval, None where the host gave nothing. CPU utilisation is the busy share of /proc/stat
    since the previous sample, so the first sample after a start has none.
    """

    def __init__(
        self,
        interval: float = HISTORY_INTERVAL,
        clock: Callable[[], float] = time.time,
        stats: Callable[[], dict] = system_stats,
        cpu_times: Callable[[], tuple[int, int] | None] = _cpu_times,
    ) -> None:
        self.interval = interval
        self._clock = clock
        self._stats = stats
        self._cpu_times = cpu_times
        self._last_times: tuple[int, int] | None = None
        self._bucket: int | None = None
        self._cpu: list[float] = []
        self._memory: list[float] = []

    def sample(self) -> tuple[dict, list | None]:
        """The current stats with ``cpu_percent``, plus the history point of the interval that just ended."""
        stats = self._stats()
        stats["cpu_percent"] = self._cpu_percent()
        bucket = int(self._clock() // self.interval)
        point = self._flush() if self._bucket is not None and bucket != self._bucket else None
        self._bucket = bucket
        if stats["cpu_percent"] is not None:
            self._cpu.append(stats["cpu_percent"])
        memory = stats.get("memory") or {}
        if memory.get("used_percent") is not None:
            self._memory.append(memory["used_percent"])
        return stats, point

    def _cpu_percent(self) -> float | None:
        times = self._cpu_times()
        last, self._last_times = self._last_times, times
        if times is None or last is None:
            return None
        idle, total = times[0] - last[0], times[1] - last[1]
        if total <= 0:
            return None
        return round(max(0.0, min(100.0, (total - idle) / total * 100)), 1)

    def _flush(self) -> list:
        start = self._bucket * self.interval
        point = [
            int(start) if float(start).is_integer() else start,
            round(sum(self._cpu) / len(self._cpu), 1) if self._cpu else None,
            round(sum(self._memory) / len(self._memory), 1) if self._memory else None,
        ]
        self._cpu, self._memory = [], []
        return point
