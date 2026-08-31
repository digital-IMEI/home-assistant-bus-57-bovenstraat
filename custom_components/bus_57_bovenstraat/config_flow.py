"""Config flow for Bus 57 Bovenstraat."""

from __future__ import annotations

from typing import Any, override

import voluptuous as vol
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.device_tracker import DOMAIN as DEVICE_TRACKER_DOMAIN
from homeassistant.components.person import DOMAIN as PERSON_DOMAIN
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .const import CONF_DAY_OFF_ENTITY, CONF_PRESENCE_ENTITY, DOMAIN, NAME


def _settings_schema(values: dict[str, Any]) -> vol.Schema:
    """Build selectors while preserving values during reconfiguration."""
    presence_key = (
        vol.Required(CONF_PRESENCE_ENTITY, default=values[CONF_PRESENCE_ENTITY])
        if CONF_PRESENCE_ENTITY in values
        else vol.Required(CONF_PRESENCE_ENTITY)
    )
    day_off_key = (
        vol.Required(CONF_DAY_OFF_ENTITY, default=values[CONF_DAY_OFF_ENTITY])
        if CONF_DAY_OFF_ENTITY in values
        else vol.Required(CONF_DAY_OFF_ENTITY)
    )
    return vol.Schema(
        {
            presence_key: EntitySelector(
                EntitySelectorConfig(
                    domain=[DEVICE_TRACKER_DOMAIN, PERSON_DOMAIN],
                )
            ),
            day_off_key: EntitySelector(EntitySelectorConfig(domain=BINARY_SENSOR_DOMAIN)),
        }
    )


class Bus57ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure the purpose-built Bus 57 integration."""

    VERSION = 1

    @staticmethod
    @callback
    @override
    def async_get_options_flow(config_entry: ConfigEntry) -> Bus57OptionsFlow:
        """Return a reconfiguration flow which reloads the integration."""
        return Bus57OptionsFlow()

    @override
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Create the fixed line tracker with private gate entities."""
        if user_input is not None:
            await self.async_set_unique_id("arriva_57_maastricht_bovenstraat_noorbeek")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=NAME, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_settings_schema({}),
        )


class Bus57OptionsFlow(OptionsFlowWithReload):
    """Allow existing installations to select or change gate entities."""

    @override
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Update private settings and reload the config entry."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_settings_schema({**self.config_entry.data, **self.config_entry.options}),
        )
