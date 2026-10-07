"""Tests for moisture source registry changes and repair flows."""

import pytest
from custom_components.plant_monitor_plus.const import (
    CONF_MOISTURE_ENTITY_ID,
    DOMAIN,
    ISSUE_MOISTURE_ENTITY_INVALID,
)
from custom_components.plant_monitor_plus.repairs import async_create_fix_flow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.repairs import ConfirmRepairFlow
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, issue_registry as ir

from . import SOURCE_ENTITY_ID, setup_integration


@pytest.mark.usefixtures("moisture_sensor")
async def test_source_renamed(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test source renaming updates the saved entity ID and reloads the plant."""
    await setup_integration(hass, mock_config_entry)
    original_runtime = mock_config_entry.runtime_data
    entity_registry.async_update_entity(
        SOURCE_ENTITY_ID, new_entity_id="sensor.renamed_moisture"
    )
    await hass.async_block_till_done()
    assert mock_config_entry.data[CONF_MOISTURE_ENTITY_ID] == "sensor.renamed_moisture"
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.runtime_data is not original_runtime
    assert (
        mock_config_entry.runtime_data.moisture_entity_id == "sensor.renamed_moisture"
    )
    assert (
        issue_registry.async_get_issue(
            DOMAIN, f"{ISSUE_MOISTURE_ENTITY_INVALID}_{mock_config_entry.entry_id}"
        )
        is None
    )


@pytest.mark.usefixtures("moisture_sensor")
async def test_source_removed(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test removing a registered source creates an issue that plant removal clears."""
    await setup_integration(hass, mock_config_entry)
    entity_registry.async_remove(SOURCE_ENTITY_ID)
    await hass.async_block_till_done()
    issue_id = f"{ISSUE_MOISTURE_ENTITY_INVALID}_{mock_config_entry.entry_id}"
    issue = issue_registry.async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_key == "moisture_entity_removed"
    assert issue.data == {"entry_id": mock_config_entry.entry_id}
    await hass.config_entries.async_remove(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is None


async def test_source_restored(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test a reload after restoring the source clears its repair issue."""
    await setup_integration(hass, mock_config_entry)
    issue_id = f"{ISSUE_MOISTURE_ENTITY_INVALID}_{mock_config_entry.entry_id}"
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is not None
    entity_registry.async_get_or_create(
        "sensor", "test", "restored-moisture", suggested_object_id="monstera_moisture"
    )
    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is None


@pytest.mark.usefixtures("moisture_sensor")
async def test_source_metadata_update(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test changing source metadata does not reload the plant."""
    await setup_integration(hass, mock_config_entry)
    original_runtime = mock_config_entry.runtime_data
    entity_registry.async_update_entity(SOURCE_ENTITY_ID, name="Soil moisture")
    await hass.async_block_till_done()
    assert mock_config_entry.runtime_data is original_runtime


@pytest.mark.parametrize(
    "issue_id",
    [
        pytest.param(
            f"{ISSUE_MOISTURE_ENTITY_INVALID}_plant-entry", id="moisture-source"
        ),
        pytest.param("other_issue", id="other"),
    ],
)
async def test_fix_flow(hass: HomeAssistant, issue_id: str) -> None:
    """Test repair issues use a message-only confirmation flow."""
    assert isinstance(
        await async_create_fix_flow(hass, issue_id, None), ConfirmRepairFlow
    )
