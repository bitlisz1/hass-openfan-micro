"""Diagnostics for OpenFAN Micro."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    dev = getattr(entry, "runtime_data", None)
    data = getattr(dev, "coordinator", None).data if dev else None
    ctrl = getattr(dev, "ctrl_state", {}) if dev else {}
    return {
        "title": entry.title,
        "host": entry.data.get("host"),
        "options": entry.options,
        "coordinator_data": data,
        "controller_state": ctrl,
        "notes": "controller_state includes last target/applied PWM, temp average, and gating flags.",
    }
