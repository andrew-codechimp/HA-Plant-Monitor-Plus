"""Binary sensors for plant_monitor_plus threshold problems."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    ATTR_CURRENT,
    ATTR_LAST_WATERED,
    ATTR_MAX,
    ATTR_MIN,
    ATTR_REASON,
    ATTR_SOURCE_ENTITY_ID,
    DOMAIN,
)

if TYPE_CHECKING:
    from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .runtime import PlantMonitorConfigEntry, PlantMonitorRuntime


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: PlantMonitorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up plant moisture problem sensor for a config entry."""
    runtime: PlantMonitorRuntime = entry.runtime_data

    entities = []
    if runtime.moisture_entity_id:
        entities.append(PlantMoistureProblemBinarySensor(runtime=runtime))
    async_add_entities(entities)


class PlantMoistureProblemBinarySensor(BinarySensorEntity):
    """Binary sensor that reports whether moisture is outside its thresholds."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_translation_key = "moisture"

    def __init__(self, runtime: PlantMonitorRuntime) -> None:
        """Initialize the moisture problem binary sensor."""
        self._runtime = runtime
        self._attr_unique_id = f"{runtime.entry.entry_id}_moisture"
        self._attr_is_on = False
        self._attr_available = True
        self._attr_extra_state_attributes: dict[str, Any] = {}

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info for this sensor."""
        return {
            "identifiers": {(DOMAIN, self._runtime.entry.entry_id)},
            "name": self._runtime.name,
        }

    async def async_added_to_hass(self) -> None:
        """Register state listener and evaluate the initial state."""
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

        self._refresh_state()

    @callback
    def _async_handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Handle source entity state changes."""
        self._refresh_state(event.data.get("new_state"))

    @callback
    def _refresh_state(self, source_state: State | None = None) -> None:
        """Re-evaluate sensor state from current moisture value and thresholds."""
        evaluation = self._runtime.evaluate_moisture(
            hass=self.hass,
            state=source_state,
        )

        self._attr_available = evaluation.available
        self._attr_is_on = evaluation.outside

        self._runtime.record_moisture_reading(evaluation.value)

        self._attr_extra_state_attributes = {
            ATTR_SOURCE_ENTITY_ID: self._runtime.moisture_entity_id,
            ATTR_CURRENT: evaluation.value,
            ATTR_MIN: evaluation.min_value,
            ATTR_MAX: evaluation.max_value,
            ATTR_REASON: evaluation.reason,
            ATTR_LAST_WATERED: self._runtime.last_watered,
        }

        self.async_write_ha_state()
