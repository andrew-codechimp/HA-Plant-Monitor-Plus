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
    vol.Required(CONF_MOISTURE_MIN, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
    vol.Required(CONF_MOISTURE_MAX, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
    vol.Required(CONF_CONDUCTIVITY_MIN, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
    vol.Required(CONF_CONDUCTIVITY_MAX, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
    vol.Required(CONF_HUMIDITY_MIN, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
    vol.Required(CONF_HUMIDITY_MAX, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
    vol.Required(CONF_TEMPERATURE_MIN, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
    vol.Required(CONF_TEMPERATURE_MAX, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
    vol.Required(CONF_ILLUMINANCE_MIN, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
    vol.Required(CONF_ILLUMINANCE_MAX, default=0): selector.NumberSelector(
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
            # Rebuild entity assignments from submitted input so cleared optional
            # selectors are actually removed from stored config data.
            updated_data = {
                key: value
                for key, value in config_entry.data.items()
                if key not in ENTITY_KEYS
            }
            updated_data[CONF_NAME] = user_input[CONF_NAME]
            for key in ENTITY_KEYS:
                if value := user_input.get(key):
                    updated_data[key] = value

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

        configured_entities = []
        for label, key in (
            ("Moisture", CONF_MOISTURE_ENTITY_ID),
            ("Conductivity", CONF_CONDUCTIVITY_ENTITY_ID),
            ("Humidity", CONF_HUMIDITY_ENTITY_ID),
            ("Temperature", CONF_TEMPERATURE_ENTITY_ID),
            ("Illuminance", CONF_ILLUMINANCE_ENTITY_ID),
        ):
            if entity_id := self.config_entry.data.get(key):
                configured_entities.append(f"- {label}: {entity_id}")

        configured_entities_text = (
            "\n".join(configured_entities)
            if configured_entities
            else "No entities are currently assigned."
        )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, suggested_values
            ),
            description_placeholders={
                "configured_entities": configured_entities_text,
            },
        )
