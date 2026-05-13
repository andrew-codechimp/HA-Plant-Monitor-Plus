"""Adds config flow for plant_monitor_plus."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CONDUCTIVITY_ENTITY_ID,
    CONF_CONDUCTIVITY_MAX,
    CONF_CONDUCTIVITY_MIN,
    CONF_HUMIDITY_ENTITY_ID,
    CONF_HUMIDITY_MAX,
    CONF_HUMIDITY_MIN,
    CONF_ILLUMINANCE_ENTITY_ID,
    CONF_ILLUMINANCE_MAX,
    CONF_ILLUMINANCE_MIN,
    CONF_MOISTURE_ENTITY_ID,
    CONF_MOISTURE_MAX,
    CONF_MOISTURE_MIN,
    CONF_TEMPERATURE_ENTITY_ID,
    CONF_TEMPERATURE_MAX,
    CONF_TEMPERATURE_MIN,
    DOMAIN,
)

ENTITY_KEYS = (
    CONF_MOISTURE_ENTITY_ID,
    CONF_CONDUCTIVITY_ENTITY_ID,
    CONF_HUMIDITY_ENTITY_ID,
    CONF_TEMPERATURE_ENTITY_ID,
    CONF_ILLUMINANCE_ENTITY_ID,
)

THRESHOLD_KEYS = (
    CONF_MOISTURE_MIN,
    CONF_MOISTURE_MAX,
    CONF_CONDUCTIVITY_MIN,
    CONF_CONDUCTIVITY_MAX,
    CONF_HUMIDITY_MIN,
    CONF_HUMIDITY_MAX,
    CONF_TEMPERATURE_MIN,
    CONF_TEMPERATURE_MAX,
    CONF_ILLUMINANCE_MIN,
    CONF_ILLUMINANCE_MAX,
)

ENTITY_SCHEMA = {
    vol.Optional(CONF_MOISTURE_ENTITY_ID): selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain="sensor", device_class=SensorDeviceClass.MOISTURE
        )
    ),
    vol.Optional(CONF_CONDUCTIVITY_ENTITY_ID): selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain="sensor", device_class=SensorDeviceClass.CONDUCTIVITY
        )
    ),
    vol.Optional(CONF_HUMIDITY_ENTITY_ID): selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain="sensor", device_class=SensorDeviceClass.HUMIDITY
        )
    ),
    vol.Optional(CONF_TEMPERATURE_ENTITY_ID): selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain="sensor", device_class=SensorDeviceClass.TEMPERATURE
        )
    ),
    vol.Optional(CONF_ILLUMINANCE_ENTITY_ID): selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain="sensor", device_class=SensorDeviceClass.ILLUMINANCE
        )
    ),
}

THRESHOLD_SCHEMA = {
    vol.Optional(CONF_MOISTURE_MIN): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
    vol.Optional(CONF_MOISTURE_MAX): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
    vol.Optional(CONF_CONDUCTIVITY_MIN): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
    vol.Optional(CONF_CONDUCTIVITY_MAX): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
    vol.Optional(CONF_HUMIDITY_MIN): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
    vol.Optional(CONF_HUMIDITY_MAX): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
    vol.Optional(CONF_TEMPERATURE_MIN): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
    vol.Optional(CONF_TEMPERATURE_MAX): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
    vol.Optional(CONF_ILLUMINANCE_MIN): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
    vol.Optional(CONF_ILLUMINANCE_MAX): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
}

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        **ENTITY_SCHEMA,
        **THRESHOLD_SCHEMA,
    }
)

RECONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        **ENTITY_SCHEMA,
    }
)

OPTIONS_SCHEMA = vol.Schema(THRESHOLD_SCHEMA)


class PlantMonitorPlusFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for Plant Monitor Plus."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> PlantMonitorPlusOptionsFlowHandler:
        """Return the options flow handler."""
        return PlantMonitorPlusOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        if user_input and not errors:
            data = {
                key: user_input[key]
                for key in (CONF_NAME, *ENTITY_KEYS)
                if key in user_input
            }
            options = {
                key: user_input[key] for key in THRESHOLD_KEYS if key in user_input
            }
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=data,
                options=options,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=USER_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the integration."""
        config_entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input and not errors:
            updated_data = dict(config_entry.data)
            updated_data.update(user_input)
            self.hass.config_entries.async_update_entry(
                config_entry,
                title=user_input[CONF_NAME],
                data=updated_data,
            )
            await self.hass.config_entries.async_reload(config_entry.entry_id)
            return self.async_abort(reason="reconfigure_successful")
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                RECONFIGURE_SCHEMA, config_entry.data
            ),
            errors=errors,
        )


class PlantMonitorPlusOptionsFlowHandler(OptionsFlow):
    """Options flow for Plant Monitor Plus."""

    def __init__(self, _config_entry: ConfigEntry) -> None:
        """Initialize options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        suggested_values = dict(self.config_entry.options)
        for key in THRESHOLD_KEYS:
            if key not in suggested_values and key in self.config_entry.data:
                suggested_values[key] = self.config_entry.data[key]

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, suggested_values
            ),
        )
