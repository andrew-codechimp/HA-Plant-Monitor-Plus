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
    CONF_MOISTURE_ENTITY_ID,
    CONF_MOISTURE_MAX,
    CONF_MOISTURE_MIN,
    CONF_WATERING_DETECTION_THRESHOLD,
    DEFAULT_MOISTURE_MAX,
    DEFAULT_MOISTURE_MIN,
    DEFAULT_WATERING_DETECTION_THRESHOLD,
    DOMAIN,
)

ENTITY_KEYS = (CONF_MOISTURE_ENTITY_ID,)

THRESHOLD_KEYS = (
    CONF_MOISTURE_MIN,
    CONF_MOISTURE_MAX,
    CONF_WATERING_DETECTION_THRESHOLD,
)

THRESHOLD_SCHEMA = {
    vol.Required(
        CONF_MOISTURE_MIN, default=DEFAULT_MOISTURE_MIN
    ): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
    vol.Required(
        CONF_MOISTURE_MAX, default=DEFAULT_MOISTURE_MAX
    ): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
    vol.Required(
        CONF_WATERING_DETECTION_THRESHOLD,
        default=DEFAULT_WATERING_DETECTION_THRESHOLD,
    ): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
        )
    ),
}

OPTIONS_SCHEMA = vol.Schema(THRESHOLD_SCHEMA)


class PlantMonitorPlusFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for Plant Monitor Plus."""

    VERSION = 1

    def _excluded_moisture_entities(
        self,
        current_entry_id: str | None = None,
    ) -> list[str]:
        """Return moisture entities already assigned to other entries."""
        excluded: list[str] = []
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if current_entry_id is not None and entry.entry_id == current_entry_id:
                continue
            excluded.append(str(entry.data[CONF_MOISTURE_ENTITY_ID]))
        return excluded

    def _entity_selector(self, current_entry_id: str | None = None) -> dict:
        """Build an entity selector excluding moisture entities in use."""
        return {
            vol.Required(CONF_MOISTURE_ENTITY_ID): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class=SensorDeviceClass.MOISTURE,
                    exclude_entities=self._excluded_moisture_entities(current_entry_id),
                )
            )
        }

    def _user_schema(self) -> vol.Schema:
        """Build user step schema."""
        return vol.Schema({
            vol.Required(CONF_NAME): str,
            **self._entity_selector(),
            **THRESHOLD_SCHEMA,
        })

    def _reconfigure_schema(self, current_entry_id: str) -> vol.Schema:
        """Build reconfigure step schema."""
        return vol.Schema({
            vol.Required(CONF_NAME): str,
            **self._entity_selector(current_entry_id),
        })

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
            data_schema=self._user_schema(),
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
                self._reconfigure_schema(config_entry.entry_id), config_entry.data
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
            description_placeholders={
                "moisture_entity_id": self.config_entry.data.get(
                    CONF_MOISTURE_ENTITY_ID, ""
                ),
            },
        )
