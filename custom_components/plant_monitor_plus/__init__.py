"""
Custom integration to create plant monitors in Home Assistant.

For more details about this integration, please refer to
https://github.com/andrew-codechimp/ha-plant-monitor-plus
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from awesomeversion.awesomeversion import AwesomeVersion
from homeassistant.const import Platform
from homeassistant.const import __version__ as HA_VERSION  # noqa: N812

from .const import MIN_HA_VERSION
from .runtime import PlantMonitorRuntime

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

    from .runtime import PlantMonitorConfigEntry

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


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
    entry: PlantMonitorConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    runtime = PlantMonitorRuntime(entry)
    await runtime.async_initialize(hass)
    entry.runtime_data = runtime

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: PlantMonitorConfigEntry,
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: PlantMonitorConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
