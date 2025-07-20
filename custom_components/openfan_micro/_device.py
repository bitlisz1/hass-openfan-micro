from typing import Any

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo, format_mac
from httpx import AsyncClient

from .const import DOMAIN


class Device:
    def __init__(self, client: AsyncClient, host: str, name: str | None = None):
        self.client = client
        self._host = host
        self._name = name

    @property
    def name(self) -> str:
        return self._name or self.hostname

    @property
    def unique_id(self) -> str:
        return f"openfan_micro_{self._host}"

    @property
    def mac(self) -> str:
        return format_mac(self._fixed_data.get("mac"))

    @property
    def version(self) -> str:
        return self._fixed_data.get("version")

    @property
    def hostname(self) -> str:
        hostname: str | None = self._fixed_data.get("hostname")
        if not hostname:
            return "uOpenFan"
        if not hostname.startswith("uOpenFan-"):
            hostname = f"uOpenFan-{hostname}"
        return hostname[:128]

    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            name=self.hostname,
            model="OpenFAN Micro",
            manufacturer="Karanovic Research",
            sw_version=self.version,
            identifiers={(DOMAIN, self.unique_id)},
            connections={(CONNECTION_NETWORK_MAC, self.mac)},
        )

    async def fetch_status(self):
        resp = await self.client.get(f"http://{self._host}/api/v0/openfan/status")
        resp.raise_for_status()
        data = resp.json()
        self._fixed_data = data.get("data", {})

    async def get_fan_status(self) -> dict[str, Any]:
        resp = await self.client.get(f"http://{self._host}/api/v0/fan/status")
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "ok":
            raise RuntimeError("Fan returned error status.")

        fan_data = data.get("data", data)
        return {
            "speed_pct": fan_data["pwm_percent"],
            "speed_rpm": fan_data["rpm"],
        }

    async def set_fan_speed(self, speed_pct: int):
        resp = await self.client.get(
            f"http://{self._host}/api/v0/fan/0/set", params={"value": int(speed_pct)}
        )
        resp.raise_for_status()
