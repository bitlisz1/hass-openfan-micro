from homeassistant.const import Platform

DOMAIN = "openfan_micro"
PLATFORMS = [Platform.FAN, Platform.SENSOR, Platform.BINARY_SENSOR]


def unique_id(host: str) -> str:
    return f"openfan_micro_{host}"
