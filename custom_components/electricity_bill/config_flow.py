"""Config flow and options flow for Electricity Bill integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .const import (
    CONF_FALLBACK_RATE,
    CONF_NAME,
    CONF_SOURCES,
    DEFAULT_FALLBACK_RATE,
    DEFAULT_NAME,
    DEFAULT_SOURCES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class ElectricityBillConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Electricity Bill."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial config flow step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}

        if user_input is not None:
            sources = user_input.get(CONF_SOURCES, [])
            if not sources:
                errors["base"] = "no_sources"
            else:
                user_data = dict(user_input)
                user_data.setdefault(CONF_NAME, DEFAULT_NAME)
                user_data.setdefault(CONF_FALLBACK_RATE, DEFAULT_FALLBACK_RATE)
                title = user_data[CONF_NAME]
                return self.async_create_entry(
                    title=title,
                    data=user_data,
                )

        schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): TextSelector(),
                vol.Required(CONF_SOURCES, default=DEFAULT_SOURCES): EntitySelector(
                    EntitySelectorConfig(
                        multiple=True,
                        domain="sensor",
                        device_class=SensorDeviceClass.ENERGY,
                    )
                ),
                vol.Optional(
                    CONF_FALLBACK_RATE, default=DEFAULT_FALLBACK_RATE
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0.0,
                        max=100.0,
                        step=0.01,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Get the options flow handler for this config entry."""
        return ElectricityBillOptionsFlow(config_entry)


class ElectricityBillOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Electricity Bill."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry

    @property
    def config_entry(self) -> ConfigEntry:
        """Return the config entry."""
        if hasattr(self, "_config_entry"):
            return self._config_entry
        return super().config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the configuration options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            sources = user_input.get(CONF_SOURCES, [])
            if not sources:
                errors["base"] = "no_sources"
            else:
                options_data = dict(user_input)
                options_data.setdefault(CONF_FALLBACK_RATE, DEFAULT_FALLBACK_RATE)
                return self.async_create_entry(
                    title="",
                    data=options_data,
                )

        current_sources = self.config_entry.options.get(
            CONF_SOURCES,
            self.config_entry.data.get(CONF_SOURCES, DEFAULT_SOURCES),
        )
        current_fallback_rate = self.config_entry.options.get(
            CONF_FALLBACK_RATE,
            self.config_entry.data.get(CONF_FALLBACK_RATE, DEFAULT_FALLBACK_RATE),
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_SOURCES, default=current_sources): EntitySelector(
                    EntitySelectorConfig(
                        multiple=True,
                        domain="sensor",
                        device_class=SensorDeviceClass.ENERGY,
                    )
                ),
                vol.Optional(
                    CONF_FALLBACK_RATE, default=current_fallback_rate
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0.0,
                        max=100.0,
                        step=0.01,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
