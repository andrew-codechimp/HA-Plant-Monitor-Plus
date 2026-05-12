"""Adds config flow for plant_monitor_plus."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import (
    CONF_CONDUCTIVITY_ENTITY_ID,
    CONF_HUMIDITY_ENTITY_ID,
    CONF_ILLUMINANCE_ENTITY_ID,
    CONF_MOISTURE_ENTITY_ID,
    CONF_TEMPERATURE_ENTITY_ID,
    DOMAIN,
)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Optional(CONF_MOISTURE_ENTITY_ID, default=[]): selector.EntitySelector(
            selector.EntitySelectorConfig(
                selector.EntitySelectorConfig(
                    domain="sensor", device_class=SensorDeviceClass.MOISTURE
                )
            )
        ),
        vol.Optional(CONF_CONDUCTIVITY_ENTITY_ID, default=[]): selector.EntitySelector(
            selector.EntitySelectorConfig(
                selector.EntitySelectorConfig(
                    domain="sensor", device_class=SensorDeviceClass.CONDUCTIVITY
                )
            )
        ),
        vol.Optional(CONF_HUMIDITY_ENTITY_ID, default=[]): selector.EntitySelector(
            selector.EntitySelectorConfig(
                selector.EntitySelectorConfig(
                    domain="sensor", device_class=SensorDeviceClass.HUMIDITY
                )
            )
        ),
        vol.Optional(CONF_TEMPERATURE_ENTITY_ID, default=[]): selector.EntitySelector(
            selector.EntitySelectorConfig(
                selector.EntitySelectorConfig(
                    domain="sensor", device_class=SensorDeviceClass.TEMPERATURE
                )
            )
        ),
        vol.Optional(CONF_ILLUMINANCE_ENTITY_ID, default=[]): selector.EntitySelector(
            selector.EntitySelectorConfig(
                selector.EntitySelectorConfig(
                    domain="sensor", device_class=SensorDeviceClass.ILLUMINANCE
                )
            )
        ),
    }
)


class PlantMonitorPlusFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for Plant Monitor Plus."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        if user_input and not errors:
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input,
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
            self.hass.config_entries.async_update_entry(
                config_entry,
                title=user_input[CONF_NAME],
                data={
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_MOISTURE_ENTITY_ID: user_input.get(CONF_MOISTURE_ENTITY_ID),
                },
            )
            await self.hass.config_entries.async_reload(config_entry.entry_id)
            return self.async_abort(reason="reconfigure_successful")
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                USER_SCHEMA, config_entry.data
            ),
            errors=errors,
        )
