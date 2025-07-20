from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ._device import Device


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry[Device], async_add_entities: AddEntitiesCallback
):
    stall_sensor = OpenFANMicroStallSensor(entry.runtime_data)
    async_add_entities([stall_sensor])


class OpenFANMicroStallSensor(BinarySensorEntity):
    def __init__(self, device: Device):
        self._ofm_device = device
        self._attr_name = f"{device.name} Stall Detected"

        self._speed_pct = 0
        self._speed_rpm = 0

        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_is_on = False
        self._unique_id = f"{device.unique_id}_stall"
        self._attr_device_info = device.device_info()

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._attr_device_info

    @property
    def is_on(self):
        return self._speed_pct > 0 and self._speed_rpm == 0

    @property
    def unique_id(self):
        return self._unique_id

    async def async_update(self):
        # True if PWM > 0 but RPM == 0
        data = await self._ofm_device.get_fan_status()
        self._speed_pct = data["speed_pct"]
        self._speed_rpm = data["speed_rpm"]
        self.async_write_ha_state()
