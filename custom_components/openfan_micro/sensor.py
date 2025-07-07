from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ._api import get_fan_status
from .const import DOMAIN, unique_id


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    host = entry.data["host"]
    name = entry.data.get("name")

    rpm = OpenFANMicroRPMSensor(host, name)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["rpm_sensor"] = rpm

    async_add_entities([rpm])


class OpenFANMicroRPMSensor(SensorEntity):
    def __init__(self, host, name=None):
        self._host = host
        self._attr_name = f"{name or 'OpenFAN Micro'} RPM"
        self._rpm = None
        self._unique_id = f"{unique_id(host)}_rpm"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id(self._host))},
            name=name or "OpenFAN Micro",
            manufacturer="Karanovic Research",
            model="OpenFAN Micro",
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._attr_device_info

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def state(self):
        return self._rpm

    @property
    def unit_of_measurement(self):
        return "RPM"

    async def async_update(self):
        data = await self.hass.async_add_executor_job(get_fan_status, self._host)
        self._rpm = data["speed_rpm"]
