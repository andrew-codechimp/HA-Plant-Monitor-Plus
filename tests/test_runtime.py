"""Tests for moisture evaluation, watering detection, and runtime subscriptions."""

from datetime import timedelta
from unittest.mock import Mock

import pytest
from custom_components.plant_monitor_plus import DATA_KEY
from custom_components.plant_monitor_plus.const import (
    CONF_WATERING_DETECTION_THRESHOLD,
    MOISTURE_LAST_VALUE,
    WATERING_DETECTION_WINDOW_MINUTES,
)
from custom_components.plant_monitor_plus.runtime import MoistureEvaluation
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant, State
from homeassistant.util import dt as dt_util

from . import LAST_WATERED_ENTITY_ID, SOURCE_ENTITY_ID, setup_integration

pytestmark = pytest.mark.usefixtures("moisture_sensor")


@pytest.mark.parametrize(
    ("source_state", "reason"),
    [
        pytest.param(None, "entity_state_missing", id="missing"),
        pytest.param(
            State(SOURCE_ENTITY_ID, "unknown"), "entity_state_missing", id="unknown"
        ),
        pytest.param(
            State(SOURCE_ENTITY_ID, "unavailable"),
            "entity_state_missing",
            id="unavailable",
        ),
        pytest.param(
            State(SOURCE_ENTITY_ID, "invalid"), "non_numeric_state", id="non-numeric"
        ),
    ],
)
async def test_invalid_evaluation(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    source_state: State | None,
    reason: str,
) -> None:
    """Test invalid source states return a reason without a value or problem."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_remove(SOURCE_ENTITY_ID)
    assert mock_config_entry.runtime_data.evaluate_moisture(
        hass, source_state
    ) == MoistureEvaluation(
        available=False,
        problem=False,
        value=None,
        minimum_value=30.0,
        maximum_value=70.0,
        reason=reason,
    )


@pytest.mark.parametrize(
    ("readings", "watered"),
    [
        pytest.param([50, 54], False, id="below-threshold"),
        pytest.param([50, 55], True, id="threshold-inclusive"),
        pytest.param([50, 52, 54, 56], True, id="gradual-increase"),
        pytest.param([50, 48, 47], False, id="drying"),
        pytest.param([50, None, 55], True, id="invalid-reading-ignored"),
    ],
)
async def test_watering_detection(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    readings: list[float | None],
    watered: bool,
) -> None:
    """Test watering is detected from an increase over the lowest reading."""
    await setup_integration(hass, mock_config_entry)
    runtime = mock_config_entry.runtime_data
    for reading in readings:
        freezer.tick(timedelta(minutes=1))
        runtime.record_moisture_reading(reading)
    assert runtime.last_watered == {True: dt_util.utcnow(), False: None}[watered]
    assert (
        hass.data[DATA_KEY].store.async_get_device(mock_config_entry.entry_id)[
            MOISTURE_LAST_VALUE
        ]
        == readings[-1]
    )


@pytest.mark.parametrize(
    "mock_config_entry",
    [pytest.param({CONF_WATERING_DETECTION_THRESHOLD: 0}, id="disabled")],
    indirect=True,
)
async def test_watering_detection_disabled(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test disabling detection prevents watering records from source increases."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_set(SOURCE_ENTITY_ID, "20")
    await hass.async_block_till_done()
    hass.states.async_set(SOURCE_ENTITY_ID, "90")
    await hass.async_block_till_done()
    assert mock_config_entry.runtime_data.last_watered is None


async def test_watering_resets_baseline(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test a detected increase updates entities once and resets the baseline."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_set(SOURCE_ENTITY_ID, "40")
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=1))
    hass.states.async_set(SOURCE_ENTITY_ID, "45")
    await hass.async_block_till_done()
    first_watered = dt_util.utcnow()
    assert hass.states.get(LAST_WATERED_ENTITY_ID).state == first_watered.isoformat()
    freezer.tick(timedelta(minutes=1))
    hass.states.async_set(SOURCE_ENTITY_ID, "46")
    await hass.async_block_till_done()
    assert mock_config_entry.runtime_data.last_watered == first_watered
    freezer.tick(timedelta(minutes=1))
    hass.states.async_set(SOURCE_ENTITY_ID, "50")
    await hass.async_block_till_done()
    assert mock_config_entry.runtime_data.last_watered == dt_util.utcnow()


async def test_restored_baseline(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test a persisted moisture baseline allows detection following a reload."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_set(SOURCE_ENTITY_ID, "40")
    await hass.async_block_till_done()
    freezer.tick(timedelta(days=2))
    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    hass.states.async_set(SOURCE_ENTITY_ID, "45")
    await hass.async_block_till_done()
    assert mock_config_entry.runtime_data.last_watered == dt_util.utcnow()


async def test_preserve_lowest_baseline(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test old higher readings are pruned while the lowest baseline is retained."""
    await setup_integration(hass, mock_config_entry)
    runtime = mock_config_entry.runtime_data
    runtime.record_moisture_reading(50)
    runtime.record_moisture_reading(40)
    freezer.tick(timedelta(minutes=WATERING_DETECTION_WINDOW_MINUTES + 1))
    runtime.record_moisture_reading(42)
    assert runtime.last_watered is None
    runtime.record_moisture_reading(45)
    assert runtime.last_watered == dt_util.utcnow()


async def test_runtime_subscriptions(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test subscribers can unsubscribe without disrupting other listeners."""
    await setup_integration(hass, mock_config_entry)
    runtime = mock_config_entry.runtime_data
    moisture_callback = Mock()
    watered_callback = Mock()
    unsubscribe_moisture = runtime.register_moisture_callback(hass, moisture_callback)
    unsubscribe_watered = runtime.register_last_watered_callback(watered_callback)
    hass.states.async_set(SOURCE_ENTITY_ID, "40")
    await hass.async_block_till_done()
    moisture_callback.assert_called_once_with(hass.states.get(SOURCE_ENTITY_ID))
    await runtime.async_set_last_watered(dt_util.utcnow() - timedelta(days=3))
    watered_callback.assert_called_once_with()
    assert runtime.last_watered_days == 3
    unsubscribe_moisture()
    unsubscribe_moisture()
    unsubscribe_watered()
    unsubscribe_watered()
    hass.states.async_set(SOURCE_ENTITY_ID, "45")
    await hass.async_block_till_done()
    moisture_callback.assert_called_once()
    watered_callback.assert_called_once()
