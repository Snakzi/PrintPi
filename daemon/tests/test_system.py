import json

from printpi_daemon.system import SystemMonitor, host_facts, parse_throttled, system_stats


def test_system_stats_shape_and_sanity():
    stats = system_stats()
    assert set(stats) >= {
        "hostname", "platform", "cpu_count", "load", "uptime_seconds", "cpu_temperature", "memory", "disk", "sampled_at",
        "throttled", "ip", "model", "os", "kernel", "arch",
    }
    assert stats["kernel"] and stats["arch"]
    assert stats["throttled"] is None or stats["throttled"]["raw"].startswith("0x")
    assert stats["hostname"]
    assert stats["cpu_count"] >= 1
    if stats["load"] is not None:
        assert len(stats["load"]) == 3
    assert stats["disk"] is not None
    assert 0 < stats["disk"]["free"] <= stats["disk"]["total"]
    assert 0 <= stats["disk"]["used_percent"] <= 100
    if stats["memory"] is not None:
        assert 0 <= stats["memory"]["used_percent"] <= 100
    json.dumps(stats)  # must be serialisable for redis


def test_host_facts_are_read_once():
    assert host_facts() is host_facts()
    assert host_facts()["kernel"]


def test_throttled_flags_are_decoded_from_vcgencmd():
    flags = parse_throttled("throttled=0x80008\n")
    assert flags["raw"] == "0x80008"
    assert flags["temperature_limit"] and flags["temperature_limit_occurred"]
    assert not flags["under_voltage"] and not flags["under_voltage_occurred"]
    now = parse_throttled("0x50005")
    assert now["under_voltage"] and now["throttled"] and now["under_voltage_occurred"] and now["throttled_occurred"]
    assert not now["frequency_capped"]
    assert parse_throttled("0x0")["raw"] == "0x0" and not any(v for k, v in parse_throttled("0x0").items() if k != "raw")
    assert parse_throttled("garbage") is None


def _monitor(interval: float = 30.0):
    clock = [1_000_000.0]
    times = [(100, 1000)]
    memory = [40.0]
    monitor = SystemMonitor(
        interval=interval,
        clock=lambda: clock[0],
        stats=lambda: {"memory": {"used_percent": memory[0]} if memory[0] is not None else None},
        cpu_times=lambda: times[0],
    )
    return monitor, clock, times, memory


def test_cpu_percent_is_the_busy_share_since_the_previous_sample():
    monitor, clock, times, _ = _monitor()
    stats, point = monitor.sample()
    assert stats["cpu_percent"] is None and point is None  # nothing to compare the first reading with
    times[0] = (150, 1200)  # 200 jiffies passed, 50 of them idle
    stats, _ = monitor.sample()
    assert stats["cpu_percent"] == 75.0
    times[0] = (150, 1200)  # no time passed at all
    assert monitor.sample()[0]["cpu_percent"] is None


def test_history_points_are_the_mean_of_an_interval():
    monitor, clock, times, memory = _monitor()
    monitor.sample()  # the reference for the first utilisation figure
    for idle_jiffies, used in ((50, 40.0), (30, 44.0), (10, 48.0)):  # 50 %, 70 %, 90 % busy of 100 jiffies
        idle, total = times[0]
        times[0] = (idle + idle_jiffies, total + 100)
        memory[0] = used
        clock[0] += 3
        _, point = monitor.sample()
        assert point is None  # still inside the interval that began at 999990
    clock[0] = 1_000_020.0  # the next interval
    _, point = monitor.sample()
    assert point == [999990, 70.0, 43.0]  # memory counts the reference sample too
    assert isinstance(point[0], int)
    _, point = monitor.sample()
    assert point is None  # the new interval is still open


def test_a_host_without_readings_yields_empty_points():
    monitor, clock, times, memory = _monitor()
    times[0] = None
    memory[0] = None
    monitor.sample()
    clock[0] += 60
    stats, point = monitor.sample()
    assert stats["cpu_percent"] is None
    assert point[1:] == [None, None]
    json.dumps(point)
