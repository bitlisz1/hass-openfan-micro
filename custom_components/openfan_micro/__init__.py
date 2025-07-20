from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client

from ._device import Device
from .const import PLATFORMS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    device = Device(
        client=get_async_client(hass),
        host=entry.data.get(CONF_HOST),
    )
    await device.fetch_status()

    entry.runtime_data = device

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
