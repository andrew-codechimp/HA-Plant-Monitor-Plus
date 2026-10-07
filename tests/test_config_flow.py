"""Tests for Plant Monitor Plus config, options, and reconfiguration flows."""

from unittest.mock import patch

import pytest
from custom_components.plant_monitor_plus.const import (
    CONF_MOISTURE_ENTITY_ID,
    CONF_MOISTURE_HIDE,
    CONF_MOISTURE_MAXIMUM,
    CONF_MOISTURE_MINIMUM,
    CONF_WATERING_DETECTION_THRESHOLD,
    DOMAIN,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from . import SOURCE_ENTITY_ID


@pytest.mark.usefixtures("mock_setup_entry", "moisture_sensor")
@pytest.mark.parametrize(
    "options",
    [
        pytest.param({}, id="defaults"),
        pytest.param(
            {
                CONF_MOISTURE_MINIMUM: 20,
                CONF_MOISTURE_MAXIMUM: 80,
                CONF_WATERING_DETECTION_THRESHOLD: 10,
                CONF_MOISTURE_HIDE: True,
            },
            id="custom-options",
        ),
    ],
)
async def test_user_flow(hass: HomeAssistant, options: dict[str, float | bool]) -> None:
    """Test a user flow separates source data from threshold options."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_NAME: "Monstera", CONF_MOISTURE_ENTITY_ID: SOURCE_ENTITY_ID, **options},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Monstera"
    assert result["data"] == {
        CONF_NAME: "Monstera",
        CONF_MOISTURE_ENTITY_ID: SOURCE_ENTITY_ID,
    }
    assert result["options"] == {
        CONF_MOISTURE_MINIMUM: 30,
        CONF_MOISTURE_MAXIMUM: 70,
        CONF_WATERING_DETECTION_THRESHOLD: 5,
        CONF_MOISTURE_HIDE: False,
        **options,
    }


@pytest.mark.parametrize(
    ("source", "excluded"),
    [
        pytest.param(SOURCE_USER, [SOURCE_ENTITY_ID], id="user"),
        pytest.param(SOURCE_RECONFIGURE, [], id="reconfigure"),
    ],
)
async def test_source_selector(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    source: str,
    excluded: list[str],
) -> None:
    """Test sources already used by another plant are excluded from selection."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": source, "entry_id": mock_config_entry.entry_id}
    )
    assert result["type"] is FlowResultType.FORM
    selector = result["data_schema"].schema[CONF_MOISTURE_ENTITY_ID]
    assert selector.config["domain"] == ["sensor"]
    assert selector.config["device_class"] == ["moisture"]
    assert selector.config["exclude_entities"] == excluded


async def test_options(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test the options form suggests saved values and updates only options."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["description_placeholders"] == {
        CONF_MOISTURE_ENTITY_ID: SOURCE_ENTITY_ID
    }
    assert {
        key.schema: key.description["suggested_value"]
        for key in result["data_schema"].schema
    } == mock_config_entry.options
    options = {
        CONF_MOISTURE_MINIMUM: 0,
        CONF_MOISTURE_MAXIMUM: 90,
        CONF_WATERING_DETECTION_THRESHOLD: 0,
        CONF_MOISTURE_HIDE: True,
    }
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], options
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options == options
    assert mock_config_entry.title == "Monstera"
    assert mock_config_entry.data == {
        CONF_NAME: "Monstera",
        CONF_MOISTURE_ENTITY_ID: SOURCE_ENTITY_ID,
    }


async def test_legacy_options_suggested_values(hass: HomeAssistant) -> None:
    """Test legacy thresholds stored in entry data are suggested in options."""
    options = {
        CONF_MOISTURE_MINIMUM: 20,
        CONF_MOISTURE_MAXIMUM: 80,
        CONF_WATERING_DETECTION_THRESHOLD: 10,
        CONF_MOISTURE_HIDE: True,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_MOISTURE_ENTITY_ID: SOURCE_ENTITY_ID, **options},
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert {
        key.schema: key.description["suggested_value"]
        for key in result["data_schema"].schema
    } == options


async def test_reconfigure(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test reconfiguration changes the name and source while keeping options."""
    mock_config_entry.add_to_hass(hass)
    options = dict(mock_config_entry.options)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": mock_config_entry.entry_id},
    )
    assert {
        key.schema: key.description["suggested_value"]
        for key in result["data_schema"].schema
    } == mock_config_entry.data

    with patch.object(hass.config_entries, "async_reload", return_value=True) as reload:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_NAME: "Fern", CONF_MOISTURE_ENTITY_ID: "sensor.fern_moisture"},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.title == "Fern"
    assert mock_config_entry.data == {
        CONF_NAME: "Fern",
        CONF_MOISTURE_ENTITY_ID: "sensor.fern_moisture",
    }
    assert mock_config_entry.options == options
    reload.assert_awaited_once_with(mock_config_entry.entry_id)
