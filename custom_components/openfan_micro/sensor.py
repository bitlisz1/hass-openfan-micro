from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo, CONNECTION_NETWORK_MAC
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from _device import Device

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    device: Device = hass.data[DOMAIN][entry.entry_id]

    rpm = OpenFANMicroRPMSensor(device)

    async_add_entities([rpm])


class OpenFANMicroRPMSensor(SensorEntity):
    def __init__(self, device: Device):
        self._ofm_device = device

        self._attr_name = f"{device.name} RPM"
        self._rpm = None
        self._unique_id = f"{device.unique_id}_rpm"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.unique_id)},
            connections={(CONNECTION_NETWORK_MAC, device.mac)},
            name=device.name,
            manufacturer="Karanovic Research",
            model="OpenFAN Micro",
            sw_version=device.version,
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
        data = await self.hass.async_add_executor_job(self._ofm_device.get_fan_status)
        self._rpm = data["speed_rpm"]
