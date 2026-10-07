"""Tests for the Plant Monitor Plus sensor platform."""

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import (
    LAST_WATERED_ENTITY_ID,
    MOISTURE_ENTITY_ID,
    SOURCE_ENTITY_ID,
    setup_integration,
)

pytestmark = pytest.mark.usefixtures("moisture_sensor")


@pytest.mark.parametrize(
    "platform",
    [
        pytest.param(Platform.SENSOR, id="sensor"),
        pytest.param(Platform.BINARY_SENSOR, id="binary-sensor"),
        pytest.param(Platform.BUTTON, id="button"),
    ],
)
async def test_entities(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    platform: Platform,
) -> None:
    """Test entity state, names, units, icons, and device associations."""
    with patch("custom_components.plant_monitor_plus.PLATFORMS", [platform]):
        await setup_integration(hass, mock_config_entry)
    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("source_state", "expected"),
    [
        pytest.param("20.5", "20.5", id="numeric"),
        pytest.param("unknown", "unavailable", id="unknown"),
        pytest.param("unavailable", "unavailable", id="unavailable"),
        pytest.param("invalid", "unavailable", id="non-numeric"),
    ],
)
async def test_source_updates(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    source_state: str,
    expected: str,
) -> None:
    """Test source reports update the moisture value and timestamp availability."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_set(SOURCE_ENTITY_ID, source_state)
    await hass.async_block_till_done()
    assert hass.states.get(MOISTURE_ENTITY_ID).state == expected
    assert (
        hass.states.get(LAST_WATERED_ENTITY_ID).state
        == {"20.5": "unknown", "unavailable": "unavailable"}[expected]
    )


async def test_source_recovery(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test removing and restoring a source state restores sensor availability."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_remove(SOURCE_ENTITY_ID)
    await hass.async_block_till_done()
    assert hass.states.get(MOISTURE_ENTITY_ID).state == "unavailable"
    hass.states.async_set(SOURCE_ENTITY_ID, "40")
    await hass.async_block_till_done()
    assert hass.states.get(MOISTURE_ENTITY_ID).state == "40.0"
    assert hass.states.get(LAST_WATERED_ENTITY_ID).state == "unknown"
