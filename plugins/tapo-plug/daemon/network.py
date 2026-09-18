"""The wire side of the Tapo plug plugin.

python-kasa speaks both the Kasa and the Tapo protocol. Discovery is a UDP broadcast
to ports 9999 (Kasa) and 20002 (Tapo); Kasa plugs answer with everything, Tapo plugs
only with model and id and talk further once signed in with the TP-Link account.

The library is asyncio, so KasaNetwork runs one event loop on its own thread and
offers blocking calls; the plugin itself stays plain threads. FakeNetwork has the
same interface with two imaginary plugs for tests and for a machine without any.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
from dataclasses import dataclass, field
from typing import Any

PLUG_FAMILIES = {"SMART.TAPOPLUG", "SMART.KASAPLUG", "IOT.SMARTPLUGSWITCH"}
DISCOVERY_SECONDS = 5
REQUEST_SECONDS = 10


class PlugError(Exception):
    pass


@dataclass
class Found:
    """A plug that answered the broadcast; connection is what reaches it again without one."""

    id: str
    host: str
    model: str
    mac: str
    name: str | None
    connection: dict = field(default_factory=dict)
    needs_auth: bool = False


@dataclass
class Reading:
    on: bool
    power_w: float | None = None
    energy_today_kwh: float | None = None
    name: str | None = None


class KasaNetwork:
    name = "kasa"

    def __init__(self, username: str, password: str) -> None:
        from kasa import Credentials

        self._credentials = Credentials(username, password) if username and password else None
        self._devices: set[Any] = set()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, name="tapo-plug-io", daemon=True)
        self._thread.start()

    @property
    def signed_in(self) -> bool:
        return self._credentials is not None

    def discover(self) -> list[Found]:
        return self._run(self._discover(), DISCOVERY_SECONDS + 3 * REQUEST_SECONDS)

    def open(self, host: str, connection: dict) -> Any:
        return self._run(self._open(host, connection), 2 * REQUEST_SECONDS)

    def read(self, device: Any) -> Reading:
        return self._run(self._read(device), 2 * REQUEST_SECONDS)

    def set_power(self, device: Any, on: bool) -> Reading:
        return self._run(self._set_power(device, on), 3 * REQUEST_SECONDS)

    def close(self, device: Any) -> None:
        self._devices.discard(device)
        try:
            self._run(device.disconnect(), REQUEST_SECONDS)
        except PlugError:
            pass

    def shutdown(self) -> None:
        """Cancel whatever is running, so a blocked caller gets a PlugError, and stop the loop."""
        loop = self._loop
        try:
            asyncio.run_coroutine_threadsafe(self._cancel_all(), loop).result(REQUEST_SECONDS)
        except Exception:  # noqa: BLE001 - best effort, the loop stops anyway
            pass
        loop.call_soon_threadsafe(loop.stop)
        self._thread.join(timeout=REQUEST_SECONDS)
        if not self._thread.is_alive():
            loop.close()

    # ---- coroutines, run on the loop thread ------------------------------------------

    async def _discover(self) -> list[Found]:
        from kasa import AuthenticationError, Discover, KasaException

        devices = await Discover.discover(
            credentials=self._credentials, discovery_timeout=DISCOVERY_SECONDS, timeout=REQUEST_SECONDS,
        )
        found: list[Found] = []
        for host, device in devices.items():
            try:
                if device.config.connection_type.device_family.value not in PLUG_FAMILIES:
                    continue
                needs_auth = False
                try:
                    await device.update()
                except AuthenticationError:
                    needs_auth = True
                except KasaException:
                    pass  # answered the broadcast but not a query; what the broadcast said is listed
                found.append(Found(
                    id=str(device.device_id),
                    host=host,
                    model=str(device.model),
                    mac=str(device.mac),
                    name=device.alias or None,
                    connection=device.config.connection_type.to_dict(),
                    needs_auth=needs_auth,
                ))
            finally:
                await device.disconnect()
        return found

    async def _open(self, host: str, connection: dict) -> Any:
        from kasa import Device, DeviceConfig
        from kasa.deviceconfig import DeviceConnectionParameters

        config = DeviceConfig(
            host=host,
            timeout=REQUEST_SECONDS,
            credentials=self._credentials,
            connection_type=DeviceConnectionParameters.from_dict(connection),
        )
        device = await Device.connect(config=config)
        self._devices.add(device)
        return device

    async def _read(self, device: Any) -> Reading:
        from kasa import Module

        await device.update()
        energy = device.modules.get(Module.Energy)
        return Reading(
            on=bool(device.is_on),
            power_w=energy.current_consumption if energy else None,
            energy_today_kwh=energy.consumption_today if energy else None,
            name=device.alias or None,
        )

    async def _set_power(self, device: Any, on: bool) -> Reading:
        if on:
            await device.turn_on()
        else:
            await device.turn_off()
        return await self._read(device)

    async def _cancel_all(self) -> None:
        for task in asyncio.all_tasks(self._loop):
            if task is not asyncio.current_task():
                task.cancel()
        for device in list(self._devices):
            try:
                await device.disconnect()
            except Exception:  # noqa: BLE001
                pass
        self._devices.clear()

    def _run(self, coroutine: Any, timeout: float) -> Any:
        future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
        try:
            return future.result(timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise PlugError("No answer") from None
        except concurrent.futures.CancelledError:
            raise PlugError("Cancelled") from None
        except Exception as exc:  # noqa: BLE001 - every kasa error becomes one the plugin can show
            raise PlugError(self._describe(exc)) from exc

    @staticmethod
    def _describe(exc: Exception) -> str:
        from kasa import AuthenticationError, TimeoutError as KasaTimeout, UnsupportedDeviceError
        from kasa.exceptions import _ConnectionError

        if isinstance(exc, AuthenticationError):
            return "TP-Link account sign-in failed"
        if isinstance(exc, (KasaTimeout, _ConnectionError, TimeoutError, OSError)):
            return "Unreachable"
        if isinstance(exc, UnsupportedDeviceError):
            return "Unsupported device"
        return str(exc) or type(exc).__name__


class FakeNetwork:
    """A Tapo P115 with energy readings and a Kasa HS100 without, on an imaginary network."""

    name = "fake"

    def __init__(self, username: str, password: str) -> None:
        self.signed_in = bool(username and password)
        self.plugs: dict[str, dict] = {
            "fake-p115": {
                "host": "192.168.1.50", "model": "P115", "mac": "AA:BB:CC:00:00:01", "name": "Printer",
                "family": "SMART.TAPOPLUG", "encryption": "KLAP", "on": False, "energy": True,
            },
            "fake-hs100": {
                "host": "192.168.1.51", "model": "HS100", "mac": "AA:BB:CC:00:00:02", "name": "Lights",
                "family": "IOT.SMARTPLUGSWITCH", "encryption": "XOR", "on": True, "energy": False,
            },
        }
        self.unreachable: set[str] = set()

    def discover(self) -> list[Found]:
        found = []
        for plug_id, plug in self.plugs.items():
            tapo = plug["family"].startswith("SMART.")
            needs_auth = tapo and not self.signed_in
            found.append(Found(
                id=plug_id, host=plug["host"], model=plug["model"], mac=plug["mac"],
                name=None if needs_auth else plug["name"],
                connection={"device_family": plug["family"], "encryption_type": plug["encryption"], "https": False},
                needs_auth=needs_auth,
            ))
        return found

    def open(self, host: str, connection: dict) -> str:
        for plug_id, plug in self.plugs.items():
            if plug["host"] == host:
                if plug_id in self.unreachable:
                    raise PlugError("Unreachable")
                if plug["family"].startswith("SMART.") and not self.signed_in:
                    raise PlugError("TP-Link account sign-in failed")
                return plug_id
        raise PlugError("Unreachable")

    def read(self, device: str) -> Reading:
        if device in self.unreachable:
            raise PlugError("Unreachable")
        plug = self.plugs[device]
        energy = plug["energy"]
        return Reading(
            on=plug["on"],
            power_w=(118.4 if plug["on"] else 0.2) if energy else None,
            energy_today_kwh=0.37 if energy else None,
            name=plug["name"],
        )

    def set_power(self, device: str, on: bool) -> Reading:
        if device in self.unreachable:
            raise PlugError("Unreachable")
        self.plugs[device]["on"] = on
        return self.read(device)

    def close(self, device: str) -> None:
        pass

    def shutdown(self) -> None:
        pass
