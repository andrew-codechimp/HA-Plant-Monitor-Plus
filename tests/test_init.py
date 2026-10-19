"""Tests for setup, reload, and cleanup of Plant Monitor Plus."""

import pytest
from custom_components.plant_monitor_plus import DATA_KEY
from custom_components.plant_monitor_plus.const import (
    CONF_MOISTURE_ENTITY_ID,
    CONF_MOISTURE_HIDE,
    DOMAIN,
    HIDDEN_MOISTURE_ENTITY_ID,
    ISSUE_MOISTURE_ENTITY_INVALID,
    SERVICE_GET_PLANT_SUMMARY,
    SERVICE_SET_PLANT_THRESHOLDS,
    SERVICE_SET_PLANT_WATERED,
)
from custom_components.plant_monitor_plus.store import (
    DATA_REGISTRY,
    async_get_registry,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)

from . import MOISTURE_ENTITY_ID, SOURCE_ENTITY_ID, setup_integration


@pytest.mark.usefixtures("moisture_sensor")
async def test_setup_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test setup creates a plant device, four entities, shared storage, and actions."""
    await setup_integration(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert hass.data[DATA_KEY].store is await async_get_registry(hass)
    assert mock_config_entry.runtime_data.name == "Monstera"
    assert (
        len(
            er.async_entries_for_config_entry(
                entity_registry, mock_config_entry.entry_id
            )
        )
        == 4
    )
    devices = dr.async_entries_for_config_entry(
        device_registry, mock_config_entry.entry_id
    )
    assert len(devices) == 1
    assert devices[0].identifiers == {(DOMAIN, mock_config_entry.entry_id)}
    assert devices[0].name == "Monstera"
    assert set(hass.services.async_services()[DOMAIN]) == {
        SERVICE_GET_PLANT_SUMMARY,
        SERVICE_SET_PLANT_THRESHOLDS,
        SERVICE_SET_PLANT_WATERED,
    }


@pytest.mark.usefixtures("moisture_sensor")
async def test_unload_entry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test unloading removes entity state listeners."""
    await setup_integration(hass, mock_config_entry)
    runtime = mock_config_entry.runtime_data
    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    assert hass.states.get(MOISTURE_ENTITY_ID).state == "unavailable"
    hass.states.async_set(SOURCE_ENTITY_ID, "90")
    await hass.async_block_till_done()
    assert runtime.last_watered is None


@pytest.mark.usefixtures("moisture_sensor")
async def test_options_reload(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test saving options reloads entities and keeps the same storage."""
    await setup_integration(hass, mock_config_entry)
    previous_runtime = mock_config_entry.runtime_data
    store = hass.data[DATA_KEY].store
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {**mock_config_entry.options, CONF_MOISTURE_HIDE: True}
    )
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.runtime_data is not previous_runtime
    assert hass.data[DATA_KEY].store is store
    assert mock_config_entry.runtime_data.moisture_hide


@pytest.mark.parametrize(
    ("mock_config_entry", "initial_hider", "expected_hider"),
    [
        pytest.param(
            {CONF_MOISTURE_HIDE: True},
            None,
            er.RegistryEntryHider.INTEGRATION,
            id="hide-source",
        ),
        pytest.param(
            {},
            er.RegistryEntryHider.INTEGRATION,
            er.RegistryEntryHider.INTEGRATION,
            id="keep-integration-hidden",
        ),
        pytest.param(
            {CONF_MOISTURE_HIDE: True},
            er.RegistryEntryHider.INTEGRATION,
            er.RegistryEntryHider.INTEGRATION,
            id="already-integration-hidden",
        ),
        pytest.param(
            {CONF_MOISTURE_HIDE: True},
            er.RegistryEntryHider.USER,
            er.RegistryEntryHider.USER,
            id="already-user-hidden",
        ),
        pytest.param(
            {},
            er.RegistryEntryHider.USER,
            er.RegistryEntryHider.USER,
            id="keep-user-hidden",
        ),
    ],
    indirect=["mock_config_entry"],
)
async def test_source_visibility(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    moisture_sensor: er.RegistryEntry,
    entity_registry: er.EntityRegistry,
    initial_hider: er.RegistryEntryHider | None,
    expected_hider: er.RegistryEntryHider | None,
) -> None:
    """Test setup and removal preserve existing source visibility choices."""
    entity_registry.async_update_entity(
        moisture_sensor.entity_id, hidden_by=initial_hider
    )
    await setup_integration(hass, mock_config_entry)
    assert entity_registry.async_get(SOURCE_ENTITY_ID).hidden_by is expected_hider
    assert await hass.config_entries.async_remove(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert entity_registry.async_get(SOURCE_ENTITY_ID).hidden_by is initial_hider


@pytest.mark.parametrize(
    "mock_config_entry", [{CONF_MOISTURE_HIDE: True}], indirect=True
)
@pytest.mark.parametrize(
    ("current_hider", "expected_hider"),
    [
        pytest.param(er.RegistryEntryHider.INTEGRATION, None, id="restore-visible"),
        pytest.param(
            er.RegistryEntryHider.USER,
            er.RegistryEntryHider.USER,
            id="preserve-user-hidden",
        ),
    ],
)
async def test_disable_source_hiding(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    moisture_sensor: er.RegistryEntry,
    entity_registry: er.EntityRegistry,
    current_hider: er.RegistryEntryHider,
    expected_hider: er.RegistryEntryHider | None,
) -> None:
    """Test persisted ownership survives reload and is cleared when disabled."""
    await setup_integration(hass, mock_config_entry)
    store = hass.data[DATA_KEY].store
    await store.async_save()
    await store.async_load()
    assert await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert (
        entity_registry.async_get(SOURCE_ENTITY_ID).hidden_by
        is er.RegistryEntryHider.INTEGRATION
    )
    assert (
        store.async_get_device(mock_config_entry.entry_id)[HIDDEN_MOISTURE_ENTITY_ID]
        == moisture_sensor.id
    )

    entity_registry.async_update_entity(SOURCE_ENTITY_ID, hidden_by=current_hider)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"], {**mock_config_entry.options, CONF_MOISTURE_HIDE: False}
    )
    await hass.async_block_till_done()
    assert entity_registry.async_get(SOURCE_ENTITY_ID).hidden_by is expected_hider
    assert (
        store.async_get_device(mock_config_entry.entry_id)[HIDDEN_MOISTURE_ENTITY_ID]
        is None
    )

    # A later owning-integration decision must no longer be attributed to us.
    entity_registry.async_update_entity(SOURCE_ENTITY_ID, hidden_by=current_hider)
    assert await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert entity_registry.async_get(SOURCE_ENTITY_ID).hidden_by is current_hider


@pytest.mark.parametrize(
    "mock_config_entry", [{CONF_MOISTURE_HIDE: True}], indirect=True
)
@pytest.mark.usefixtures("moisture_sensor")
@pytest.mark.parametrize(
    ("current_hider", "expected_hider"),
    [
        pytest.param(er.RegistryEntryHider.INTEGRATION, None, id="restore-visible"),
        pytest.param(
            er.RegistryEntryHider.USER,
            er.RegistryEntryHider.USER,
            id="preserve-user-hidden",
        ),
    ],
)
async def test_remove_entry_hidden_renamed_source(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    current_hider: er.RegistryEntryHider,
    expected_hider: er.RegistryEntryHider | None,
) -> None:
    """Test removal restores a renamed source from storage without runtime data."""
    await setup_integration(hass, mock_config_entry)
    store = hass.data[DATA_KEY].store
    await store.async_save()
    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    hass.data.pop(DATA_KEY)
    hass.data.pop(DATA_REGISTRY)
    renamed = "sensor.renamed_moisture"
    entity_registry.async_update_entity(
        SOURCE_ENTITY_ID, new_entity_id=renamed, hidden_by=current_hider
    )

    assert await hass.config_entries.async_remove(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert entity_registry.async_get(renamed).hidden_by is expected_hider


@pytest.mark.parametrize(
    "mock_config_entry", [{CONF_MOISTURE_HIDE: True}], indirect=True
)
@pytest.mark.usefixtures("moisture_sensor")
async def test_replaced_hidden_source(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test ownership does not transfer to an entity reusing the source ID."""
    await setup_integration(hass, mock_config_entry)
    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entity_registry.async_remove(SOURCE_ENTITY_ID)
    hass.states.async_remove(SOURCE_ENTITY_ID)
    replacement = entity_registry.async_get_or_create(
        "sensor",
        "test",
        "replacement-moisture",
        suggested_object_id="monstera_moisture",
        hidden_by=er.RegistryEntryHider.INTEGRATION,
    )
    assert replacement.entity_id == SOURCE_ENTITY_ID

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_remove(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert (
        entity_registry.async_get(SOURCE_ENTITY_ID).hidden_by
        is er.RegistryEntryHider.INTEGRATION
    )


@pytest.mark.usefixtures("moisture_sensor")
async def test_source_unique_id(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test a stored entity registry ID resolves to the current entity ID."""
    source = entity_registry.async_get(SOURCE_ENTITY_ID)
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        data={**mock_config_entry.data, CONF_MOISTURE_ENTITY_ID: source.id},
    )
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.data[CONF_MOISTURE_ENTITY_ID] == SOURCE_ENTITY_ID


async def test_missing_source(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test a missing source loads unavailable entities and creates a repair issue."""
    await setup_integration(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get(MOISTURE_ENTITY_ID).state == "unavailable"
    issue = issue_registry.async_get_issue(
        DOMAIN, f"{ISSUE_MOISTURE_ENTITY_INVALID}_{mock_config_entry.entry_id}"
    )
    assert issue is not None
    assert issue.is_fixable
    assert issue.translation_key == "moisture_entity_removed"
    assert issue.translation_placeholders == {
        "entity_id": SOURCE_ENTITY_ID,
        "name": "Monstera",
    }
