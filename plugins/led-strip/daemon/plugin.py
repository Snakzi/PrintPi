"""LED strip plugin: one solid colour on a WS281x or SK6812 strip.

The pin picks the hardware backend:

- GPIO 12, 18, 13, 19 (PWM) and 21 (PCM) go through rpi_ws281x, which drives the
  strip by DMA and needs /dev/mem; install.sh opens that for the daemon's group.
  Works up to the Pi 4, the Pi 5 has no compatible PWM block.
- GPIO 10 (SPI0) and 20 (SPI1) go through spidev: every strip bit becomes one
  SPI byte at 6.4 MHz, no root needed, works on every Pi. SPI must be enabled.

Without a hardware library, on a development machine, the frame is kept in
memory so the UI can be used; the status says "simulated".

The strip is also the printer's light: the status reports it as printer_light with
its colour, printer_light_on / printer_light_off switch it and printer_light_color
recolours it, which puts a light button with a colour picker into the status bar of
the web app.
"""

from __future__ import annotations

import os
import re
import sys

from printpi_daemon.plugins import PluginBase, PluginError

STRIP_TYPES = {
    "ws2812b": "GRB",
    "ws2811": "RGB",
    "sk6812": "GRB",
    "sk6812_rgbw": "GRBW",
}
PWM_CHANNELS = {12: 0, 18: 0, 13: 1, 19: 1, 21: 0}
SPI_DEVICES = {10: ("/dev/spidev0.0", 0), 20: ("/dev/spidev1.0", 1)}
SPI_HZ = 6_400_000
SPI_RESET_BYTES = 100  # 125 us of low level at 6.4 MHz, above the 80 us latch time
SPI_BUFSIZ = "/sys/module/spidev/parameters/bufsiz"
COLOR_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")

Pixel = tuple[int, int, int, int]  # r, g, b, w


class Backend:
    name = "simulated"

    def __init__(self, count: int, order: str) -> None:
        self.count = count
        self.order = order
        self.hint: str | None = None
        self.pixels: list[Pixel] = []

    def show(self, pixels: list[Pixel]) -> None:
        self.pixels = pixels

    def close(self) -> None:
        pass


class Ws281xBackend(Backend):
    name = "ws281x"

    def __init__(self, count: int, order: str, pin: int) -> None:
        super().__init__(count, order)
        from rpi_ws281x import PixelStrip, ws

        strip_types = {"RGB": ws.WS2811_STRIP_RGB, "GRB": ws.WS2811_STRIP_GRB, "GRBW": ws.SK6812_STRIP_GRBW}
        self._strip = PixelStrip(count, pin, 800_000, 10, False, 255, PWM_CHANNELS[pin], strip_types[order])
        self._strip.begin()
        if pin != 21 and os.path.isdir("/sys/module/snd_bcm2835"):
            self.hint = "Onboard audio uses the same PWM block; set dtparam=audio=off if the strip flickers."

    def show(self, pixels: list[Pixel]) -> None:
        from rpi_ws281x import Color

        for index, (r, g, b, w) in enumerate(pixels):
            self._strip.setPixelColor(index, Color(r, g, b, w))
        self._strip.show()
        self.pixels = pixels

    def close(self) -> None:
        strip, self._strip = self._strip, None
        if strip is not None:
            strip._cleanup()


class SpiBackend(Backend):
    name = "spi"

    def __init__(self, count: int, order: str, pin: int) -> None:
        super().__init__(count, order)
        import spidev

        device, bus = SPI_DEVICES[pin]
        if not os.path.exists(device):
            raise PluginError(f"{device} does not exist; enable SPI (dtparam=spi=on) and reboot")
        self._spi = spidev.SpiDev()
        self._spi.open(bus, 0)
        self._spi.max_speed_hz = SPI_HZ
        self._spi.mode = 0
        frame = count * len(order) * 8 + 2 * SPI_RESET_BYTES
        bufsiz = self._bufsiz()
        if bufsiz and frame > bufsiz:
            self.hint = (f"{count} LEDs need {frame} bytes per frame but spidev.bufsiz is {bufsiz}; "
                         f"add spidev.bufsiz={frame} to the kernel command line.")

    @staticmethod
    def _bufsiz() -> int:
        try:
            with open(SPI_BUFSIZ, encoding="ascii") as handle:
                return int(handle.read().strip())
        except (OSError, ValueError):
            return 0

    def show(self, pixels: list[Pixel]) -> None:
        data = bytearray(SPI_RESET_BYTES)
        for r, g, b, w in pixels:
            for channel in self.order:
                value = {"R": r, "G": g, "B": b, "W": w}[channel]
                for bit in range(7, -1, -1):
                    data.append(0xF0 if value >> bit & 1 else 0xC0)
        data += bytes(SPI_RESET_BYTES)
        self._spi.writebytes2(data)
        self.pixels = pixels

    def close(self) -> None:
        spi, self._spi = self._spi, None
        if spi is not None:
            spi.close()


class Plugin(PluginBase):
    _backend: Backend | None = None

    def start(self) -> None:
        strip_type = str(self.settings.get("strip_type", "ws2812b"))
        order = STRIP_TYPES.get(strip_type)
        if order is None:
            raise PluginError(f"unknown strip type {strip_type!r}")
        count = int(self.settings.get("led_count", 30))
        pin = int(self.settings.get("gpio_pin", 18))
        if count < 1:
            raise PluginError("led_count must be at least 1")
        self.state.setdefault("power", True)
        self.state.setdefault("color", "#ffffff")
        self.state.setdefault("brightness", 50)
        self._backend = self._open_backend(count, order, pin)
        self._render()

    def stop(self) -> None:
        backend, self._backend = self._backend, None
        if backend is None:
            return
        try:
            backend.show([(0, 0, 0, 0)] * backend.count)
        finally:
            backend.close()

    def handle(self, action: str, value) -> None:
        if action == "set_power":
            self.state["power"] = bool(value)
        elif action in ("printer_light_on", "printer_light_off"):
            self.state["power"] = action == "printer_light_on"
        elif action in ("set_color", "printer_light_color"):
            match = COLOR_RE.match(str(value or ""))
            if not match:
                raise PluginError(f"{value!r} is not a #rrggbb colour")
            self.state["color"] = "#" + match.group(1).lower()
        elif action == "set_brightness":
            try:
                brightness = int(value)
            except (TypeError, ValueError):
                raise PluginError(f"{value!r} is not a brightness") from None
            self.state["brightness"] = max(0, min(100, brightness))
        else:
            raise PluginError(f"unknown action {action!r}")
        self.save_state()
        self._render()

    def status(self) -> dict:
        backend = self._backend
        return {
            "backend": backend.name if backend else None,
            "hint": backend.hint if backend else None,
            "led_count": backend.count if backend else 0,
            "power": bool(self.state.get("power", True)),
            "color": self.state.get("color", "#ffffff"),
            "brightness": int(self.state.get("brightness", 50)),
            "printer_light": {
                "name": "LED strip",
                "on": bool(self.state.get("power", True)),
                "color": self.state.get("color", "#ffffff"),
            },
        }

    def _open_backend(self, count: int, order: str, pin: int) -> Backend:
        if pin not in SPI_DEVICES and pin not in PWM_CHANNELS:
            raise PluginError(f"GPIO {pin} cannot drive a strip; use a PWM, PCM or SPI pin")
        if self.settings.get("driver") == "simulated":
            return Backend(count, order)
        try:
            if pin in SPI_DEVICES:
                return SpiBackend(count, order, pin)
            return Ws281xBackend(count, order, pin)
        except ImportError as exc:
            if sys.platform == "linux":
                raise PluginError(f"{exc}; the plugin requirements are not installed") from exc
            backend = Backend(count, order)
            backend.hint = f"{exc.name} is not available on this machine, running simulated"
            return backend

    def _render(self) -> None:
        backend = self._backend
        if backend is None:
            return
        pixel: Pixel = (0, 0, 0, 0)
        if self.state.get("power", True):
            rgb = int(str(self.state.get("color", "#ffffff")).lstrip("#"), 16)
            scale = max(0, min(100, int(self.state.get("brightness", 50)))) / 100
            pixel = (round((rgb >> 16 & 0xFF) * scale), round((rgb >> 8 & 0xFF) * scale), round((rgb & 0xFF) * scale), 0)
        backend.show([pixel] * backend.count)
