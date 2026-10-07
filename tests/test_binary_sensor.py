"""Tests for moisture problem states and change timestamps."""

from datetime import timedelta

import pytest
from custom_components.plant_monitor_plus.const import (
    ATTR_PROBLEM_LAST_MODIFIED,
    ATTR_REASON,
    CONF_MOISTURE_MAXIMUM,
    CONF_MOISTURE_MINIMUM,
)
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from . import PROBLEM_ENTITY_ID, SOURCE_ENTITY_ID, setup_integration

pytestmark = pytest.mark.usefixtures("moisture_sensor")


@pytest.mark.parametrize(
    ("value", "expected_state", "reason"),
    [
        pytest.param("29", "on", "too_dry", id="dry"),
        pytest.param("30", "off", "ok", id="minimum-inclusive"),
        pytest.param("70", "off", "ok", id="maximum-inclusive"),
        pytest.param("71", "on", "too_wet", id="wet"),
    ],
)
async def test_moisture_problem(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    value: str,
    expected_state: str,
    reason: str,
) -> None:
    """Test thresholds include their endpoints and reject invalid source states."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_set(SOURCE_ENTITY_ID, value)
    await hass.async_block_till_done()
    state = hass.states.get(PROBLEM_ENTITY_ID)
    assert state.state == expected_state
    assert state.attributes[ATTR_REASON] == reason


@pytest.mark.parametrize(
    "mock_config_entry",
    [
        pytest.param({CONF_MOISTURE_MINIMUM: 0}, id="minimum-disabled"),
        pytest.param({CONF_MOISTURE_MAXIMUM: 0}, id="maximum-disabled"),
    ],
    indirect=True,
)
async def test_disabled_thresholds(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test disabling either threshold leaves the problem state unknown."""
    await setup_integration(hass, mock_config_entry)
    state = hass.states.get(PROBLEM_ENTITY_ID)
    assert state.state == "unknown"
    assert state.attributes[ATTR_REASON] == "threshold_disabled"
    assert mock_config_entry.runtime_data.moisture_problem_state is None


async def test_problem_change_timestamp(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test only authoritative problem transitions update the modification time."""
    await setup_integration(hass, mock_config_entry)
    assert mock_config_entry.runtime_data.moisture_problem_last_modified is None
    freezer.tick(timedelta(minutes=1))
    changed_at = dt_util.utcnow()
    hass.states.async_set(SOURCE_ENTITY_ID, "20")
    await hass.async_block_till_done()
    assert mock_config_entry.runtime_data.moisture_problem_last_modified == changed_at

    for value in ("19", "unavailable", "18"):
        freezer.tick(timedelta(minutes=1))
        hass.states.async_set(SOURCE_ENTITY_ID, value)
        await hass.async_block_till_done()
        assert mock_config_entry.runtime_data.moisture_problem_state is True
        assert (
            mock_config_entry.runtime_data.moisture_problem_last_modified == changed_at
        )

    freezer.tick(timedelta(minutes=1))
    recovered_at = dt_util.utcnow()
    hass.states.async_set(SOURCE_ENTITY_ID, "40")
    await hass.async_block_till_done()
    assert mock_config_entry.runtime_data.moisture_problem_state is False
    assert (
        hass.states.get(PROBLEM_ENTITY_ID).attributes[ATTR_PROBLEM_LAST_MODIFIED]
        == recovered_at
    )
