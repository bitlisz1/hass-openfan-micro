from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .binary_sensor import OpenFANMicroStallSensor
from .const import DOMAIN, PLATFORMS
from .fan import OpenFANMicroEntity
from .sensor import OpenFANMicroRPMSensor


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    host = entry.data["host"]
    name = entry.data.get("name")

    fan_entity = OpenFANMicroEntity(host, name)
    rpm_sensor = OpenFANMicroRPMSensor(host, name)
    stall_sensor = OpenFANMicroStallSensor(name, fan_entity, rpm_sensor)

    async_add_entities([fan_entity, rpm_sensor, stall_sensor])


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
