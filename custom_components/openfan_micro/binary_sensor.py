from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, unique_id

if TYPE_CHECKING:
    from .fan import OpenFANMicroEntity
    from .sensor import OpenFANMicroRPMSensor


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    # Import your fan class
    fan_entity = hass.data["openfan_micro"]["fan_entity"]
    rpm_sensor = hass.data["openfan_micro"]["rpm_sensor"]

    stall_sensor = OpenFANMicroStallSensor(
        name=fan_entity.name,
        fan_entity=fan_entity,
        rpm_sensor=rpm_sensor,
    )
    async_add_entities([stall_sensor])


class OpenFANMicroStallSensor(BinarySensorEntity):

    def __init__(
        self, name: str, fan_entity: "OpenFANMicroEntity", rpm_sensor: "OpenFANMicroRPMSensor"
    ):
        self._name = f"{name} Stall Detected"
        self._fan_entity = fan_entity
        self._rpm_sensor = rpm_sensor
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_is_on = False
        self._unique_id = f"{unique_id(fan_entity._host)}_stall"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id(fan_entity._host))},
            name=name or "OpenFAN Micro",
            manufacturer="Karanovic Research",
            model="OpenFAN Micro",
        )

    @property
    def is_on(self):
        # True if PWM > 0 but RPM == 0
        return self._fan_entity.percentage > 0 and self._rpm_sensor.state == 0

    @property
    def name(self):
        return self._name

    async def async_update(self):
        await self._fan_entity.async_update()
        await self._rpm_sensor.async_update()
        self.async_write_ha_state()
