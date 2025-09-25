"""OpenFAN Micro integration setup.

This module wires up the config entry to the platforms and stores
the device object on `entry.runtime_data` to be consumed by platforms.
"""
from __future__ import annotations
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from ._device import Device

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.FAN, Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Create the device object and forward to platforms."""
    host = entry.data.get("host")
    name = entry.data.get("name")
    mac = entry.data.get("mac")

    if not host:
        _LOGGER.error("%s: missing 'host' in config entry", DOMAIN)
        return False

    dev = Device(hass, host, name, mac=mac)
    await dev.async_first_refresh()

    entry.runtime_data = dev
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the platforms for this config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
