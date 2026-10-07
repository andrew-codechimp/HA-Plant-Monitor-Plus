"""Tests for plant summary, watering, and threshold actions."""

from datetime import timedelta

import pytest
import voluptuous as vol
from custom_components.plant_monitor_plus.const import (
    CONF_MOISTURE_ENTITY_ID,
    CONF_MOISTURE_MAXIMUM,
    CONF_MOISTURE_MINIMUM,
    DOMAIN,
    SERVICE_GET_PLANT_SUMMARY,
    SERVICE_PARAM_DATETIME,
    SERVICE_SET_PLANT_THRESHOLDS,
    SERVICE_SET_PLANT_WATERED,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from homeassistant.config_entries import ConfigEntryDisabler, ConfigEntryState
from homeassistant.const import ATTR_CONFIG_ENTRY_ID, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util

from . import LAST_WATERED_ENTITY_ID, SOURCE_ENTITY_ID, setup_integration

pytestmark = pytest.mark.usefixtures("moisture_sensor")


@pytest.mark.parametrize(
    ("data", "timestamp"),
    [
        pytest.param({}, "2026-07-01T12:00:00+00:00", id="now"),
        pytest.param(
            {SERVICE_PARAM_DATETIME: "2026-06-28T14:00:00+02:00"},
            "2026-06-28T12:00:00+00:00",
            id="offset-to-utc",
        ),
        pytest.param(
            {SERVICE_PARAM_DATETIME: "2026-06-28T12:00:00"},
            "2026-06-28T11:00:00+00:00",
            id="naive-local-to-utc",
        ),
    ],
)
async def test_set_plant_watered(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    data: dict[str, str],
    timestamp: str,
) -> None:
    """Test watering actions update the runtime and entities with UTC timestamps."""
    await hass.config.async_set_time_zone("Europe/London")
    await setup_integration(hass, mock_config_entry)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_PLANT_WATERED,
        {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id, **data},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert mock_config_entry.runtime_data.last_watered == dt_util.parse_datetime(
        timestamp
    )
    assert hass.states.get(LAST_WATERED_ENTITY_ID).state == timestamp


@pytest.mark.parametrize(
    "timestamp",
    [
        pytest.param("invalid", id="invalid-string"),
        pytest.param("2026-02-30T12:00:00", id="invalid-date"),
    ],
)
async def test_invalid_watered_datetime(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, timestamp: str
) -> None:
    """Test invalid timestamps raise a translated error without changing history."""
    await setup_integration(hass, mock_config_entry)
    with pytest.raises(ServiceValidationError) as error:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_PLANT_WATERED,
            {
                ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                SERVICE_PARAM_DATETIME: timestamp,
            },
            blocking=True,
        )
    assert error.value.translation_domain == DOMAIN
    assert error.value.translation_key == "invalid_datetime"
    assert mock_config_entry.runtime_data.last_watered is None


@pytest.mark.parametrize(
    "thresholds",
    [
        pytest.param({CONF_MOISTURE_MINIMUM: 20}, id="minimum-only"),
        pytest.param({CONF_MOISTURE_MAXIMUM: 80}, id="maximum-only"),
        pytest.param(
            {CONF_MOISTURE_MINIMUM: 0, CONF_MOISTURE_MAXIMUM: 0}, id="disable"
        ),
    ],
)
async def test_set_thresholds(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    thresholds: dict[str, float],
) -> None:
    """Test threshold actions preserve other options and watering history on reload."""
    await setup_integration(hass, mock_config_entry)
    options = dict(mock_config_entry.options)
    watered_at = dt_util.utcnow() - timedelta(days=2)
    await mock_config_entry.runtime_data.async_set_last_watered(watered_at)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_PLANT_THRESHOLDS,
        {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id, **thresholds},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.options == {**options, **thresholds}
    assert mock_config_entry.runtime_data.last_watered == watered_at


@pytest.mark.parametrize(
    "thresholds",
    [
        pytest.param({}, id="no-thresholds"),
        pytest.param({CONF_MOISTURE_MINIMUM: 30}, id="unchanged"),
    ],
)
async def test_unchanged_thresholds(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    thresholds: dict[str, float],
) -> None:
    """Test empty or unchanged thresholds do not reload the plant."""
    await setup_integration(hass, mock_config_entry)
    runtime = mock_config_entry.runtime_data
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_PLANT_THRESHOLDS,
        {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id, **thresholds},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert mock_config_entry.runtime_data is runtime


@pytest.mark.parametrize(
    "thresholds",
    [
        pytest.param({CONF_MOISTURE_MINIMUM: -1}, id="below-zero"),
        pytest.param({CONF_MOISTURE_MAXIMUM: 101}, id="above-hundred"),
    ],
)
async def test_invalid_thresholds(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    thresholds: dict[str, float],
) -> None:
    """Test action schemas reject thresholds outside the percentage range."""
    await setup_integration(hass, mock_config_entry)
    options = dict(mock_config_entry.options)
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_PLANT_THRESHOLDS,
            {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id, **thresholds},
            blocking=True,
        )
    assert mock_config_entry.options == options


@pytest.mark.parametrize(
    "action", [SERVICE_SET_PLANT_THRESHOLDS, SERVICE_SET_PLANT_WATERED]
)
async def test_unknown_entry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, action: str
) -> None:
    """Test actions reject a missing config entry."""
    await setup_integration(hass, mock_config_entry)
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, action, {ATTR_CONFIG_ENTRY_ID: "missing-entry"}, blocking=True
        )


async def test_get_plant_summary(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test summaries categorize multiple plants and include their metadata."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_set(SOURCE_ENTITY_ID, "20")
    await hass.async_block_till_done()
    await mock_config_entry.runtime_data.async_set_last_watered(
        dt_util.utcnow() - timedelta(days=2)
    )
    for name, value in (("Fern", "80"), ("Orchid", "unavailable")):
        entity_id = f"sensor.{name.lower()}_moisture"
        hass.states.async_set(entity_id, value)
        entry = MockConfigEntry(
            domain=DOMAIN,
            title=name,
            entry_id=name.lower(),
            data={CONF_NAME: name, CONF_MOISTURE_ENTITY_ID: entity_id},
            options=mock_config_entry.options,
        )
        await setup_integration(hass, entry)
    result = await hass.services.async_call(
        DOMAIN, SERVICE_GET_PLANT_SUMMARY, blocking=True, return_response=True
    )
    assert result is not None
    for plant in result["plants"]:
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, plant[ATTR_CONFIG_ENTRY_ID])}
        )
        assert plant["device_id"] == device.id
        plant["device_id"] = "device-id"
    assert result == snapshot


async def test_summary_skips_inactive_plants(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test disabled plants, disabled devices, and entries without runtimes are skipped."""
    await setup_integration(hass, mock_config_entry)
    device = device_registry.async_get_device(
        identifiers={(DOMAIN, mock_config_entry.entry_id)}
    )
    device_registry.async_update_device(
        device.id, disabled_by=dr.DeviceEntryDisabler.USER
    )
    MockConfigEntry(domain=DOMAIN, title="Not loaded", data={}).add_to_hass(hass)
    MockConfigEntry(
        domain=DOMAIN, title="Disabled", data={}, disabled_by=ConfigEntryDisabler.USER
    ).add_to_hass(hass)
    result = await hass.services.async_call(
        DOMAIN, SERVICE_GET_PLANT_SUMMARY, blocking=True, return_response=True
    )
    assert result == {"plants": [], "too_dry": [], "too_wet": [], "unavailable": []}
