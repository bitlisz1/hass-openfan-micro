from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from ._api import get_fan_status
from .const import DOMAIN, unique_id


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    host = entry.data["host"]
    name = entry.data.get("name")
    async_add_entities([OpenFANMicroRPMSensor(host, name)])


class OpenFANMicroRPMSensor(SensorEntity):
    def __init__(self, host, name=None):
        self._host = host
        self._attr_name = f"{name or 'OpenFAN Micro'} RPM"
        self._rpm = None
        self._unique_id = f"{unique_id(host)}_rpm"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, unique_id(self._host))},
            name=self.name,
            manufacturer="Karanovic Research",
            model="OpenFAN Micro",
        )

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def state(self):
        return self._rpm

    @property
    def unit_of_measurement(self):
        return "RPM"

    def update(self):
        self._rpm = get_fan_status(self._host)["speed_rpm"]
