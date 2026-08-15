"""Custom integration to create plant monitors in Home Assistant.

For more details about this integration, please refer to
https://github.com/andrew-codechimp/ha-plant-monitor-plus
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import voluptuous as vol
from awesomeversion import AwesomeVersion

from homeassistant.const import Platform, __version__ as HA_VERSION  # noqa: N812
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.util.hass_dict import HassKey

from .const import (
    CONF_MOISTURE_ENTITY_ID,
    DOMAIN,
    ISSUE_MOISTURE_ENTITY_INVALID,
    MIN_HA_VERSION,
)
from .runtime import PlantMonitorPlusRuntime
from .services import async_setup_services, async_unload_services
from .store import PlantMonitorStorage, async_get_registry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

    from .runtime import PlantMonitorPlusConfigEntry

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]


@dataclass
class PlantMonitorData:
    """Typed integration data stored in hass.data."""

    store: PlantMonitorStorage


DATA_KEY: HassKey[PlantMonitorData] = HassKey(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:  # noqa: ARG001
    """Integration setup."""
    if AwesomeVersion(HA_VERSION) < AwesomeVersion(MIN_HA_VERSION):  # pragma: no cover
        msg = (
            "This integration requires at least Home Assistant version "
            f"{MIN_HA_VERSION}, you are running version {HA_VERSION}. "
            "Please upgrade Home Assistant to continue using this integration."
        )
        _LOGGER.critical(msg)
        return False

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlantMonitorPlusConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    if DATA_KEY not in hass.data:
        shared_store = await async_get_registry(hass)
        await shared_store.async_load()
        hass.data[DATA_KEY] = PlantMonitorData(store=shared_store)

    await async_setup_services(hass)

    entity_registry = er.async_get(hass)
    configured_entity_id = str(entry.data[CONF_MOISTURE_ENTITY_ID])
    try:
        resolved_entity_id = er.async_validate_entity_id(
            entity_registry,
            configured_entity_id,
        )
    except vol.Invalid:
        _LOGGER.warning(
            "Configured moisture source entity %s is not in the registry; "
            "plant monitor entities will be unavailable until it appears",
            configured_entity_id,
        )
    else:
        if resolved_entity_id != configured_entity_id:
            hass.config_entries.async_update_entry(
                entry,
                data={
                    **entry.data,
                    CONF_MOISTURE_ENTITY_ID: resolved_entity_id,
                },
            )

    integration_data = hass.data[DATA_KEY]

    runtime = PlantMonitorPlusRuntime(entry, integration_data.store)

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=runtime.name,
    )

    runtime.restore_recent_moisture_readings()
    entry.runtime_data = runtime
    entry.async_on_unload(runtime.async_setup_moisture_entity_watcher(hass))

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: PlantMonitorPlusConfigEntry,
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and not hass.config_entries.async_entries(DOMAIN):
        await async_unload_services(hass)
        hass.data.pop(DATA_KEY, None)
    return unload_ok


async def async_reload_entry(
    hass: HomeAssistant,
    entry: PlantMonitorPlusConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_entry(
    hass: HomeAssistant,
    entry: PlantMonitorPlusConfigEntry,
) -> None:
    """Handle removal of a config entry."""
    if DATA_KEY in hass.data:
        store = hass.data[DATA_KEY].store
    else:
        store = PlantMonitorStorage(hass)
        await store.async_load()

    store.async_delete_device(entry.entry_id)

    ir.async_delete_issue(
        hass,
        DOMAIN,
        f"{ISSUE_MOISTURE_ENTITY_INVALID}_{entry.entry_id}",
    )
