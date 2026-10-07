"""Tests for the manually watered button."""

import pytest
from custom_components.plant_monitor_plus import DATA_KEY
from custom_components.plant_monitor_plus.const import ATTR_LAST_WATERED, LAST_WATERED
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from . import (
    BUTTON_ENTITY_ID,
    LAST_WATERED_ENTITY_ID,
    MOISTURE_ENTITY_ID,
    PROBLEM_ENTITY_ID,
    setup_integration,
)


@pytest.mark.usefixtures("moisture_sensor")
async def test_press_watered(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test pressing the button persists watering and updates all plant entities."""
    await setup_integration(hass, mock_config_entry)
    freezer.move_to("2026-07-02T14:30:00+00:00")
    watered_at = dt_util.utcnow()
    await hass.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: BUTTON_ENTITY_ID}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(BUTTON_ENTITY_ID).state == watered_at.isoformat()
    assert hass.states.get(LAST_WATERED_ENTITY_ID).state == watered_at.isoformat()
    assert mock_config_entry.runtime_data.last_watered == watered_at
    assert (
        hass.data[DATA_KEY].store.async_get_device(mock_config_entry.entry_id)[
            LAST_WATERED
        ]
        == watered_at
    )
    for entity_id in (MOISTURE_ENTITY_ID, PROBLEM_ENTITY_ID):
        assert hass.states.get(entity_id).attributes[ATTR_LAST_WATERED] == watered_at
