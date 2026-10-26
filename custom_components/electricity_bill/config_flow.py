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
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .calc import parse_tariff_tiers
from .const import (
    CONF_AI_TASK_ENTITY,
    CONF_BUDGET_THRESHOLD,
    CONF_CUTOFF_DAY_30,
    CONF_CUTOFF_DAY_31,
    CONF_CUTOFF_DAY_FEB,
    CONF_FALLBACK_RATE,
    CONF_FT_RATE,
    CONF_MAIN_METER,
    CONF_NAME,
    CONF_RESET_BUTTON,
    CONF_SERVICE_CHARGE,
    CONF_SOURCES,
    CONF_TARIFF_PROFILE,
    CONF_TARIFF_TIERS,
    CONF_VAT_PERCENT,
    DEFAULT_TARIFF_PROFILE,
    PROFILE_CUSTOM,
    TARIFF_PROFILES,
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
        self._init_data: dict[str, Any] = {}

    @property
    def config_entry(self) -> ConfigEntry:
        """Return the config entry."""
        if hasattr(self, "_config_entry"):
            return self._config_entry
        return super().config_entry

    async def async_step_tariff(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Second options page: tariff profile, extra charges, billing day, budget."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get(CONF_TARIFF_PROFILE) == PROFILE_CUSTOM:
                try:
                    parse_tariff_tiers(user_input.get(CONF_TARIFF_TIERS, ""))
                except ValueError:
                    errors[CONF_TARIFF_TIERS] = "invalid_tiers"
            if not errors:
                data = {**self._init_data, **user_input}
                return self.async_create_entry(title="", data=data)

        def cur(key: str) -> Any:
            return self.config_entry.options.get(key, self.config_entry.data.get(key))

        def number(key: str, lo: float, hi: float, step: float) -> tuple[Any, Any]:
            return (
                vol.Optional(key, description={"suggested_value": cur(key)}),
                NumberSelector(
                    NumberSelectorConfig(min=lo, max=hi, step=step, mode=NumberSelectorMode.BOX)
                ),
            )

        schema: dict[Any, Any] = {
            vol.Optional(
                CONF_TARIFF_PROFILE, default=cur(CONF_TARIFF_PROFILE) or DEFAULT_TARIFF_PROFILE
            ): SelectSelector(
                SelectSelectorConfig(
                    options=TARIFF_PROFILES,
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="tariff_profile",
                )
            ),
            vol.Optional(
                CONF_TARIFF_TIERS, description={"suggested_value": cur(CONF_TARIFF_TIERS)}
            ): TextSelector(),
        }
        for key, lo, hi, step in (
            (CONF_FT_RATE, -10.0, 10.0, 0.0001),
            (CONF_SERVICE_CHARGE, 0.0, 100000.0, 0.01),
            (CONF_VAT_PERCENT, 0.0, 100.0, 0.01),
            (CONF_CUTOFF_DAY_30, 1, 28, 1),
            (CONF_CUTOFF_DAY_31, 1, 28, 1),
            (CONF_CUTOFF_DAY_FEB, 1, 28, 1),
            (CONF_BUDGET_THRESHOLD, 0.0, 10000000.0, 1.0),
        ):
            k, sel = number(key, lo, hi, step)
            schema[k] = sel
        return self.async_show_form(
            step_id="tariff", data_schema=vol.Schema(schema), errors=errors
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the configuration options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            sources = user_input.get(CONF_SOURCES, [])
            if not sources and not user_input.get(CONF_MAIN_METER):
                errors["base"] = "no_sources"
            else:
                options_data = dict(user_input)
                options_data.setdefault(CONF_FALLBACK_RATE, DEFAULT_FALLBACK_RATE)
                self._init_data = options_data
                return await self.async_step_tariff()

        current_sources = self.config_entry.options.get(
            CONF_SOURCES,
            self.config_entry.data.get(CONF_SOURCES, DEFAULT_SOURCES),
        )
        current_fallback_rate = self.config_entry.options.get(
            CONF_FALLBACK_RATE,
            self.config_entry.data.get(CONF_FALLBACK_RATE, DEFAULT_FALLBACK_RATE),
        )
        current_ai_task = self.config_entry.options.get(
            CONF_AI_TASK_ENTITY,
            self.config_entry.data.get(CONF_AI_TASK_ENTITY),
        )

        current_main = self.config_entry.options.get(
            CONF_MAIN_METER, self.config_entry.data.get(CONF_MAIN_METER)
        )
        current_reset = self.config_entry.options.get(
            CONF_RESET_BUTTON, self.config_entry.data.get(CONF_RESET_BUTTON)
        )

        options_schema: dict[Any, Any] = {}
        options_schema[
            vol.Optional(CONF_MAIN_METER, description={"suggested_value": current_main})
        ] = EntitySelector(
            EntitySelectorConfig(domain="sensor", device_class=SensorDeviceClass.ENERGY)
        )
        options_schema[
            vol.Optional(CONF_RESET_BUTTON, description={"suggested_value": current_reset})
        ] = EntitySelector(EntitySelectorConfig(domain="button"))
        options_schema[vol.Optional(CONF_SOURCES, default=current_sources)] = EntitySelector(
            EntitySelectorConfig(
                multiple=True,
                domain="sensor",
                device_class=SensorDeviceClass.ENERGY,
            )
        )
        options_schema.update({
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
        })

        if current_ai_task:
            options_schema[
                vol.Optional(CONF_AI_TASK_ENTITY, default=current_ai_task)
            ] = EntitySelector(EntitySelectorConfig(domain="ai_task"))
        else:
            options_schema[
                vol.Optional(CONF_AI_TASK_ENTITY)
            ] = EntitySelector(EntitySelectorConfig(domain="ai_task"))

        schema = vol.Schema(options_schema)

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
