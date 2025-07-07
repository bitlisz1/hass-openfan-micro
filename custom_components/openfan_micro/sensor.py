from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .fan import get_fan_status


class OpenFANMicroRPMSensor(SensorEntity):
    def __init__(self, host, name=None):
        self._host = host
        self._attr_name = f"{name or 'OpenFAN Micro'} RPM"
        self._rpm = None
        self._unique_id = f"openfan_micro_{host}_rpm"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            name=self.name,
            manufacturer="Karanovic Research",
            model="OpenFAN Micro",
        )

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def state(self):
        return self._rpm

    @property
    def unit_of_measurement(self):
        return "RPM"

    def update(self):
        self._rpm = get_fan_status(self._host)["speed_rpm"]
