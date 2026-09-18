"""Command line entry point.

  printpi-daemon --repl                                   talk to the fake printer
  printpi-daemon --port rfc2217://printer.local:3333 --repl
  printpi-daemon --redis redis://127.0.0.1:6379/0                (systemd; waits for a
                                                                  connect command from the UI)

Every option can also come from the environment: PRINTPI_PORT, PRINTPI_BAUD,
PRINTPI_SERIAL_LOG, PRINTPI_REDIS_URL.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import threading

from . import __version__
from .printer import Printer, PrinterError
from .serial_log import SerialLog

log = logging.getLogger("printpi")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="printpi-daemon", description="PrintPi printer daemon")
    parser.add_argument("--port", default=os.environ.get("PRINTPI_PORT", "fake://"),
                        help="serial device, rfc2217:// or socket:// URL, or fake:// (default: %(default)s)")
    parser.add_argument("--baud", type=int, default=int(os.environ.get("PRINTPI_BAUD", "115200")))
    parser.add_argument("--serial-log", default=os.environ.get("PRINTPI_SERIAL_LOG"),
                        help="file that receives every TX/RX line with timestamps")
    parser.add_argument("--redis", default=os.environ.get("PRINTPI_REDIS_URL"),
                        help="redis URL; enables the bridge to the web app")
    parser.add_argument("--repl", action="store_true", help="interactive G-code prompt on stdin")
    parser.add_argument("--autoconnect", action=argparse.BooleanOptionalAction, default=None,
                        help="open --port at start (default: yes for --repl, no for the bridge)")
    parser.add_argument("-v", "--verbose", action="store_true", help="log every serial line to stderr")
    parser.add_argument("--version", action="version", version=f"printpi-daemon {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    if not args.repl and not args.redis:
        print("nothing to do: pass --repl for an interactive session or --redis for the bridge",
              file=sys.stderr)
        return 2

    printer = Printer(args.port, args.baud, serial_log=SerialLog(args.serial_log))
    autoconnect = args.repl if args.autoconnect is None else args.autoconnect
    if args.repl:
        return repl(printer, autoconnect=autoconnect)
    return serve(printer, args.redis, autoconnect=autoconnect)


def serve(printer: Printer, redis_url: str, *, autoconnect: bool) -> int:
    from .bridge import RedisBridge

    bridge = RedisBridge(redis_url, printer)
    bridge.start()
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    if autoconnect:
        try:
            printer.connect()
        except PrinterError as exc:
            log.error("initial connect failed: %s (waiting for a connect command)", exc)
    log.info("daemon running, default port %s", printer.port_url)
    stop.wait()
    log.info("shutting down")
    bridge.stop()
    if bridge.printer.connected:
        bridge.printer.disconnect()
    return 0


def repl(printer: Printer, *, autoconnect: bool) -> int:
    try:
        import readline  # noqa: F401 - line editing and history for input()
    except ImportError:
        pass

    from .job import SerialJobRunner

    printer.on_line = lambda direction, line: print(("< " if direction == "rx" else "> ") + line)
    jobs = SerialJobRunner(lambda: printer)
    print(f"PrintPi REPL on {printer.port_url}. Type G-code, /help for commands, /quit to leave.")
    if autoconnect:
        _try(printer.connect)
    while True:
        try:
            text = input("printpi> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text.startswith("/"):
            if text in ("/quit", "/q", "/exit"):
                break
            _repl_command(printer, jobs, text)
            continue
        _try(printer.send, text)
    jobs.stop()
    if printer.connected:
        printer.disconnect()
    return 0


def _repl_command(printer: Printer, jobs, text: str) -> None:
    words = text[1:].split()
    command = words[0]
    if command == "help":
        print("  /state       show the state snapshot\n  /temps       show temperatures\n"
              "  /connect     open the port\n  /disconnect  close the port\n"
              "  /stop        emergency stop (M112)\n"
              "  /print FILE  stream a G-code file\n  /pause /resume /cancel /again  control the print\n"
              "  /job         show the print job\n  /quit        leave")
    elif command == "state":
        for key, value in printer.state.to_dict().items():
            print(f"  {key}: {value}")
    elif command == "temps":
        for sensor, reading in printer.state.temperatures.items():
            print(f"  {sensor}: {reading.actual:.1f} / {reading.target}")
    elif command == "connect":
        _try(printer.connect)
    elif command == "disconnect":
        _try(printer.disconnect)
    elif command == "stop":
        _try(printer.emergency_stop)
    elif command == "print":
        if len(words) < 2:
            print("usage: /print FILE")
        else:
            _try(jobs.start, " ".join(words[1:]))
    elif command in ("pause", "resume", "cancel"):
        _try(getattr(jobs, command))
    elif command == "again":
        _try(jobs.restart)
    elif command == "job":
        job = jobs.state
        if job is None:
            print("  no print job")
        else:
            for key, value in job.to_dict().items():
                print(f"  {key}: {value}")
    else:
        print(f"unknown command {text!r}, try /help")


def _try(func, *args) -> None:
    from .job import JobError

    try:
        func(*args)
    except (PrinterError, JobError) as exc:
        print(f"!! {exc}")


if __name__ == "__main__":
    sys.exit(main())
