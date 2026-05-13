"""Buttons for plant_monitor_plus."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.button import ButtonEntity

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .runtime import PlantMonitorConfigEntry, PlantMonitorRuntime


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: PlantMonitorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up buttons for a config entry."""
    runtime: PlantMonitorRuntime = entry.runtime_data
    async_add_entities([PlantWateredButton(runtime)])


class PlantWateredButton(ButtonEntity):
    """Button to manually mark a plant as watered now."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_translation_key = "watered"

    def __init__(self, runtime: PlantMonitorRuntime) -> None:
        """Initialize the watered button."""
        self._runtime = runtime
        self._attr_unique_id = f"{runtime.entry.entry_id}_watered"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info for this button."""
        return {
            "identifiers": {(DOMAIN, self._runtime.entry.entry_id)},
            "name": self._runtime.name,
        }

    async def async_press(self) -> None:
        """Handle button press."""
        self._runtime.mark_watered_now()
