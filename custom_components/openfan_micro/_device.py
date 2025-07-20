from typing import Any
from httpx import AsyncClient, HTTPError


class Device:

    def __init__(self, client: AsyncClient, host: str, name: str | None = None):
        self.client = client
        self._host = host
        self._name = name or "OpenFAN Micro"

    @property
    def unique_id(self) -> str:
        return f"openfan_micro_{self._host}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def mac(self) -> str:
        return self._fixed_data.get("mac")

    @property
    def version(self) -> str:
        return self._fixed_data.get("version")

    @property
    def hostname(self) -> str:
        return self._fixed_data.get("hostname")

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
        resp = self.client.get(
            f"http://{self._host}/api/v0/fan/0/set", params={"value": int(speed_pct)}
        )
        resp.raise_for_status()

    @staticmethod
    async def test_connection(client: AsyncClient, host: str) -> bool:
        """Check if the OpenFAN Micro device is reachable and responding."""
        try:
            resp = client.get(f"http://{host}/api/v0/fan/status")
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != "ok":
                return False
            return True
        except (HTTPError, ValueError):
            return False
