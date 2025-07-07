import requests
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def get_fan_status(host):
    url = f"http://{host}/api/v0/fan/status"
    resp = requests.get(url, timeout=5)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "ok":
        raise RuntimeError("Fan returned error status.")

    return {
        "speed_pct": data["pwm_percent"],
        "speed_rpm": data["rpm"],
    }


def set_fan_speed(host, speed_pct):
    url = f"http://{host}/api/v0/fan/0/set"
    params = {"value": int(speed_pct)}
    resp = requests.get(url, params=params, timeout=5)
    resp.raise_for_status()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    host = entry.data["host"]
    name = entry.data.get("name")
    async_add_entities([OpenFANMicroEntity(host, name)])


class OpenFANMicroEntity(FanEntity):
    def __init__(self, host, name=None):
        self._host = host
        self._attr_name = name or "OpenFAN Micro"
        self._attr_supported_features = FanEntityFeature.SET_SPEED
        self._speed_pct = 0

        self._unique_id = f"openfan_micro_{host}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, self.unique_id)
            },
            name=self.name,
            manufacturer="Karanovic Research",
            model="OpenFAN Micro",
        )

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def is_on(self):
        return self._speed_pct > 0

    @property
    def percentage(self):
        return self._speed_pct

    async def async_update(self):
        data = await self.hass.async_add_executor_job(get_fan_status, self._host)
        self._speed_pct = data["speed_pct"]

    async def async_set_percentage(self, percentage: int) -> None:
        await self.hass.async_add_executor_job(set_fan_speed, self._host, percentage)
        self._speed_pct = percentage
