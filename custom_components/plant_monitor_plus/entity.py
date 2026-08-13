"""Base entity class for plant_monitor_plus."""

from typing import TYPE_CHECKING

from homeassistant.const import MATCH_ALL
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN

if TYPE_CHECKING:
    from .runtime import PlantMonitorPlusRuntime


class PlantMonitorPlusEntity(Entity):
    """Base entity for plant monitor entities."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _unrecorded_attributes = frozenset({MATCH_ALL})

    def __init__(self, runtime: PlantMonitorPlusRuntime, key: str) -> None:
        """Initialize the entity."""
        self._runtime = runtime
        self._attr_unique_id = f"{runtime.entry.entry_id}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._runtime.entry.entry_id)},
            name=self._runtime.name,
        )
