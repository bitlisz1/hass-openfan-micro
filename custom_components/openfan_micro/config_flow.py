from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME
import voluptuous as vol
import requests
from requests.exceptions import RequestException

from .const import DOMAIN


def test_connection(host):
    """Check if the OpenFAN Micro device is reachable and responding."""
    try:
        resp = requests.get(f"http://{host}/api/v0/fan/status", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "ok":
            return False
        return True
    except (RequestException, ValueError):
        return False


class OpenFANMicroConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            is_valid = await self.hass.async_add_executor_job(test_connection, host)

            if is_valid:
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME) or f"OpenFAN Micro ({host})",
                    data=user_input,
                )
            else:
                errors["base"] = "cannot_connect"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_NAME, default=""): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
