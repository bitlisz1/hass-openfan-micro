from typing import Any, Optional

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ._device import Device
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry[Device], async_add_entities: AddEntitiesCallback
):
    fan = OpenFANMicroEntity(entry.runtime_data)

    async_add_entities([fan])


class OpenFANMicroEntity(FanEntity):
    def __init__(self, device: Device):
        self._ofm_device = device
        # Last speed when turning off, default to 50%
        self.last_speed = 50
        self._attr_name = device.hostname
        self._speed_pct = 0
        self._unique_id = device.unique_id
        self._attr_device_info = device.device_info()

    @property
    def supported_features(self) -> FanEntityFeature:
        """Flag supported features."""
        return FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_OFF | FanEntityFeature.TURN_ON

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._attr_device_info

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
        data = await self._ofm_device.get_fan_status()
        self._speed_pct = data["speed_pct"]

    async def async_set_percentage(self, percentage: int) -> None:
        await self._ofm_device.set_fan_speed(percentage)
        self._speed_pct = percentage

    async def async_turn_on(
        self,
        speed: Optional[str] = None,
        percentage: Optional[int] = None,
        preset_mode: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        await self._ofm_device.set_fan_speed(percentage or self.last_speed)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        self.last_speed = self.percentage
        await self._ofm_device.set_fan_speed(0)
