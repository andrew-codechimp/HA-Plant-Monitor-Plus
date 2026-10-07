"""Tests for the Plant Monitor Plus integration."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

SOURCE_ENTITY_ID = "sensor.monstera_moisture"
MOISTURE_ENTITY_ID = "sensor.monstera_moisture_plus"
PROBLEM_ENTITY_ID = "binary_sensor.monstera_moisture_status"
LAST_WATERED_ENTITY_ID = "sensor.monstera_last_watered"
BUTTON_ENTITY_ID = "button.monstera_watered"


async def setup_integration(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    """Set up the integration from a config entry."""
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
