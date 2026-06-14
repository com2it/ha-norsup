"""Config flow for Norsup / Fairland Pool Heat Pump integration."""
from __future__ import annotations

import socket
import struct
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, DEFAULT_PORT

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_NAME, default="Pool Heat Pump"): str,
    }
)


def _test_connection(host: str, port: int) -> bool:
    """Test if we can connect to the heat pump converter."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        # Send a simple FC03 request to slave 1
        req = struct.pack(">HHHBBHH", 0x0001, 0, 6, 1, 3, 1011, 1)
        sock.send(req)
        sock.settimeout(3)
        resp = sock.recv(256)
        sock.close()
        return len(resp) > 0
    except Exception:
        return False


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input by testing the connection."""
    host = data[CONF_HOST]
    port = data[CONF_PORT]

    can_connect = await hass.async_add_executor_job(_test_connection, host, port)
    if not can_connect:
        raise CannotConnect

    return {"title": data.get(CONF_NAME, f"Pool Heat Pump ({host})")}


class NorsupConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Norsup."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""
