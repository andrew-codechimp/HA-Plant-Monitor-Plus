"""Buttons for plant_monitor_plus."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity
from homeassistant.util import dt as dt_util

from .entity import PlantMonitorPlusEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .runtime import PlantMonitorPlusConfigEntry, PlantMonitorPlusRuntime


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: PlantMonitorPlusConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up buttons for a config entry."""
    runtime: PlantMonitorPlusRuntime = entry.runtime_data
    async_add_entities([PlantWateredButton(runtime)])


class PlantWateredButton(PlantMonitorPlusEntity, ButtonEntity):
    """Button to manually mark a plant as watered now."""

    _attr_translation_key = "watered"
    _attr_name = "Watered"

    def __init__(self, runtime: PlantMonitorPlusRuntime) -> None:
        """Initialize the watered button."""
        super().__init__(runtime)
        self._attr_unique_id = f"{runtime.entry.entry_id}_watered"

    async def async_press(self) -> None:
        """Handle button press."""
        await self._runtime.async_set_last_watered(dt_util.utcnow())
