"""Sensors for plant_monitor_plus."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .runtime import PlantMonitorConfigEntry, PlantMonitorRuntime


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: PlantMonitorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors for a config entry."""
    runtime: PlantMonitorRuntime = entry.runtime_data
    async_add_entities([PlantLastWateredSensor(runtime)])


class PlantLastWateredSensor(SensorEntity):
    """Sensor exposing the last watered timestamp."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_translation_key = "last_watered"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_native_value: datetime | None = None

    def __init__(self, runtime: PlantMonitorRuntime) -> None:
        """Initialize the last watered sensor."""
        self._runtime = runtime
        self._attr_unique_id = f"{runtime.entry.entry_id}_last_watered"
        self._attr_available = True

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info for this sensor."""
        return {
            "identifiers": {(DOMAIN, self._runtime.entry.entry_id)},
            "name": self._runtime.name,
        }

    async def async_added_to_hass(self) -> None:
        """Register listeners and evaluate initial state."""
        await super().async_added_to_hass()

        entity_id = self._runtime.moisture_entity_id
        if entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [entity_id],
                    self._async_handle_state_change,
                )
            )

        self.async_on_remove(
            self._runtime.register_last_watered_callback(
                self._async_handle_last_watered_update,
            )
        )

        self._refresh_state()

    @callback
    def _async_handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Handle source entity state changes."""
        self._refresh_state(event.data.get("new_state"))

    @callback
    def _async_handle_last_watered_update(self) -> None:
        """Handle runtime updates to last watered."""
        self._attr_native_value = self._runtime.last_watered
        self.async_write_ha_state()

    @callback
    def _refresh_state(self, source_state: State | None = None) -> None:
        """Refresh sensor availability/value from runtime state."""
        evaluation = self._runtime.evaluate_moisture(
            hass=self.hass,
            state=source_state,
        )
        self._attr_available = evaluation.available
        self._attr_native_value = self._runtime.last_watered
        self.async_write_ha_state()
