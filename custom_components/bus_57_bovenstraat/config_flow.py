"""Config flow for Bus 57 Bovenstraat."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from .const import DOMAIN, NAME


class Bus57ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure the purpose-built Bus 57 integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create the fixed Gulpen -> Maastricht / Bovenstraat tracker."""
        if user_input is not None:
            await self.async_set_unique_id("arriva_57_maastricht_bovenstraat_noorbeek")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=NAME, data={})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
        )
