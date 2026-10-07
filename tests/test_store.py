"""Tests for persistent plant history and delayed saves."""

from datetime import timedelta
from typing import Any

import pytest
from custom_components.plant_monitor_plus import DATA_KEY
from custom_components.plant_monitor_plus.const import (
    LAST_WATERED,
    MOISTURE_LAST_VALUE,
    MOISTURE_PROBLEM_LAST_MODIFIED,
    MOISTURE_PROBLEM_STATE,
)
from custom_components.plant_monitor_plus.store import (
    SAVE_DELAY,
    STORAGE_KEY,
    STORAGE_VERSION_MAJOR,
    STORAGE_VERSION_MINOR,
    PlantMonitorStorage,
    async_get_registry,
)
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from . import LAST_WATERED_ENTITY_ID, SOURCE_ENTITY_ID, setup_integration


@pytest.mark.usefixtures("moisture_sensor")
@pytest.mark.parametrize(
    "minor_version",
    [pytest.param(0, id="migrated"), pytest.param(STORAGE_VERSION_MINOR, id="current")],
)
async def test_load_storage(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
    minor_version: int,
) -> None:
    """Test saved timestamps and moisture history load from current and old storage."""
    hass_storage[STORAGE_KEY] = {
        "version": STORAGE_VERSION_MAJOR,
        "minor_version": minor_version,
        "key": STORAGE_KEY,
        "data": {
            "devices": [
                {
                    "device_id": mock_config_entry.entry_id,
                    LAST_WATERED: "2026-06-28T12:00:00+00:00",
                    MOISTURE_LAST_VALUE: 40.0,
                    MOISTURE_PROBLEM_STATE: False,
                    MOISTURE_PROBLEM_LAST_MODIFIED: "2026-06-29T12:00:00+00:00",
                }
            ],
        },
    }
    await setup_integration(hass, mock_config_entry)
    runtime = mock_config_entry.runtime_data
    assert runtime.last_watered == dt_util.parse_datetime("2026-06-28T12:00:00+00:00")
    assert runtime.last_watered_days == 3
    assert runtime.moisture_problem_last_modified == dt_util.parse_datetime(
        "2026-06-29T12:00:00+00:00"
    )
    assert hass.states.get(LAST_WATERED_ENTITY_ID).state == "2026-06-28T12:00:00+00:00"


async def test_storage_crud(hass: HomeAssistant) -> None:
    """Test create, update, duplicate creation, deletion, and explicit saving."""
    store = await async_get_registry(hass)
    assert await async_get_registry(hass) is store
    assert store.async_get_device("plant") is None
    assert store.async_get_devices() == {}
    assert store.async_create_device("plant", {MOISTURE_LAST_VALUE: 40}) is not None
    assert store.async_create_device("plant", {MOISTURE_LAST_VALUE: 90}) is None
    assert store.async_get_device("plant")[MOISTURE_LAST_VALUE] == 40
    updated = store.async_update_device("plant", {MOISTURE_LAST_VALUE: 50})
    assert updated.moisture_last_value == 50
    assert store.async_get_devices()["plant"][MOISTURE_LAST_VALUE] == 50
    await store.async_save()
    reloaded = PlantMonitorStorage(hass)
    await reloaded.async_load()
    assert reloaded.async_get_devices() == store.async_get_devices()
    assert store.async_delete_device("plant")
    assert not store.async_delete_device("plant")
    assert store.async_get_devices() == {}


@pytest.mark.usefixtures("moisture_sensor")
async def test_delayed_save(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test watering and moisture changes reach storage after the save delay."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_set(SOURCE_ENTITY_ID, "40")
    await hass.async_block_till_done()
    watered_at = dt_util.utcnow()
    await mock_config_entry.runtime_data.async_set_last_watered(watered_at)
    freezer.tick(timedelta(seconds=SAVE_DELAY - 1))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done(wait_background_tasks=True)
    assert STORAGE_KEY not in hass_storage
    freezer.tick(timedelta(seconds=1))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done(wait_background_tasks=True)
    assert hass_storage[STORAGE_KEY]["data"]["devices"] == [
        {
            "device_id": mock_config_entry.entry_id,
            MOISTURE_LAST_VALUE: 40.0,
            LAST_WATERED: watered_at.isoformat(),
            MOISTURE_PROBLEM_STATE: False,
            MOISTURE_PROBLEM_LAST_MODIFIED: None,
        }
    ]


@pytest.mark.usefixtures("moisture_sensor")
async def test_remove_entry_history(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test removing a plant deletes its saved history."""
    await setup_integration(hass, mock_config_entry)
    store = hass.data[DATA_KEY].store
    await mock_config_entry.runtime_data.async_set_last_watered(dt_util.utcnow())
    assert store.async_get_device(mock_config_entry.entry_id) is not None
    assert await hass.config_entries.async_remove(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert store.async_get_device(mock_config_entry.entry_id) is None
