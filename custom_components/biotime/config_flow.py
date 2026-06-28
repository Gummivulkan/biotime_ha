"""Config- und Options-Flow (UI-Einrichtung)."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BioTimeApi, BioTimeAuthError, BioTimeConnectionError
from .const import CONF_USERCODE, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_USERCODE): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class BioTimeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Einrichtung über die UI."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = BioTimeApi(
                session,
                user_input[CONF_HOST],
                user_input[CONF_PORT],
                user_input[CONF_USERCODE],
                user_input[CONF_PASSWORD],
            )
            try:
                await api.async_login()
                terminal = await api.async_get_terminal_info()
            except BioTimeAuthError:
                errors["base"] = "invalid_auth"
            except BioTimeConnectionError:
                errors["base"] = "cannot_connect"
            else:
                serial = terminal.get("serial", "unknown")
                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"BioTime ({serial})", data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> BioTimeOptionsFlow:
        return BioTimeOptionsFlow()


class BioTimeOptionsFlow(OptionsFlow):
    """Poll-Intervall anpassen."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                    int, vol.Range(min=15, max=3600)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
