"""Buttons for plant_monitor_plus."""

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
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
    entity_description = ButtonEntityDescription(
        key="watered",
        translation_key="watered",
    )
    async_add_entities([PlantWateredButton(entity_description, runtime)])


class PlantWateredButton(PlantMonitorPlusEntity, ButtonEntity):
    """Button to manually mark a plant as watered now."""

    def __init__(
        self,
        entity_description: ButtonEntityDescription,
        runtime: PlantMonitorPlusRuntime,
    ) -> None:
        """Initialize the watered button."""
        super().__init__(runtime, entity_description.key)
        self.entity_description = entity_description

    async def async_press(self) -> None:
        """Handle button press."""
        await self._runtime.async_set_last_watered(dt_util.utcnow())
