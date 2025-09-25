"""Polling coordinator for OpenFAN Micro."""
from __future__ import annotations
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OpenFanApi

_LOGGER = logging.getLogger(__name__)


class OpenFanCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, api: OpenFanApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="OpenFAN Micro",
            update_interval=timedelta(seconds=5),
        )
        self.api = api

    async def _async_update_data(self) -> dict:
        try:
            rpm, pwm = await self.api.get_status()
            data = {"rpm": int(max(0, rpm)), "pwm": int(max(0, min(100, pwm)))}
            _LOGGER.debug("OpenFAN Micro update OK (%s): %s", getattr(self.api, "_host", "?"), data)
            return data
        except Exception as err:
            _LOGGER.error("OpenFAN Micro update failed (%s): %r", getattr(self.api, "_host", "?"), err)
            raise UpdateFailed(f"Failed to update OpenFAN Micro: {err}") from err
