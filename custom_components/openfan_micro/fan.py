from typing import Any, Optional

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.helpers.device_registry import DeviceInfo

from ._api import get_fan_status, set_fan_speed
from .const import DOMAIN, unique_id


class OpenFANMicroEntity(FanEntity):
    def __init__(self, host, name=None):
        self._host = host
        # Last speed when turning off, default to 50%
        self.last_speed = 50
        self._attr_name = name or "OpenFAN Micro"
        self._speed_pct = 0
        self._unique_id = unique_id(host)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id(self._host))},
            name=name or "OpenFAN Micro",
            manufacturer="Karanovic Research",
            model="OpenFAN Micro",
        )

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
        data = await self.hass.async_add_executor_job(get_fan_status, self._host)
        self._speed_pct = data["speed_pct"]

    async def async_set_percentage(self, percentage: int) -> None:
        await self.hass.async_add_executor_job(set_fan_speed, self._host, percentage)
        self._speed_pct = percentage

    async def async_turn_on(
        self,
        speed: Optional[str] = None,
        percentage: Optional[int] = None,
        preset_mode: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        await self.hass.async_add_executor_job(
            set_fan_speed, self._host, percentage or self.last_speed
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        self.last_speed = self.percentage
        await self.hass.async_add_executor_job(set_fan_speed, self._host, 0)
