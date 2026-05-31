"""Sensors for plant_monitor_plus."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import PERCENTAGE
from homeassistant.core import callback

from .const import (
    ATTR_CURRENT_MOISTURE,
    ATTR_LAST_MODIFIED,
    ATTR_LAST_WATERED,
    ATTR_MAXIMUM_MOISTURE,
    ATTR_MINIMUM_MOISTURE,
    ATTR_REASON,
    ATTR_SOURCE_ENTITY_ID,
)
from .entity import PlantMonitorPlusEntity

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.core import HomeAssistant, State
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .runtime import PlantMonitorPlusConfigEntry, PlantMonitorPlusRuntime


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: PlantMonitorPlusConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors for a config entry."""
    runtime: PlantMonitorPlusRuntime = entry.runtime_data
    entities: list[SensorEntity] = [PlantLastWateredSensor(runtime)]
    if runtime.moisture_entity_id:
        entities.append(PlantMoistureSensor(runtime))
    async_add_entities(entities)


class PlantMoistureSensor(PlantMonitorPlusEntity, SensorEntity):
    """Sensor exposing the current moisture value from the watched source entity."""

    _attr_translation_key = "moisture"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 0
    _attr_native_value: float | None = None

    def __init__(self, runtime: PlantMonitorPlusRuntime) -> None:
        """Initialize the moisture sensor."""
        super().__init__(runtime)
        self._attr_unique_id = f"{runtime.entry.entry_id}_moisture_value"
        self._attr_available = True

    async def async_added_to_hass(self) -> None:
        """Register listeners and evaluate initial state."""
        await super().async_added_to_hass()

        self.async_on_remove(
            self._runtime.register_moisture_callback(
                self.hass,
                self._refresh_state,
            )
        )

        self._refresh_state()

    @callback
    def _refresh_state(self, source_state: State | None = None) -> None:
        """Refresh sensor value from runtime moisture evaluation."""
        evaluation = self._runtime.evaluate_moisture(
            hass=self.hass,
            state=source_state,
        )
        self._attr_available = evaluation.available
        self._attr_native_value = evaluation.moisture_value
        self._attr_extra_state_attributes = {
            ATTR_SOURCE_ENTITY_ID: self._runtime.moisture_entity_id,
            ATTR_CURRENT_MOISTURE: evaluation.moisture_value,
            ATTR_MINIMUM_MOISTURE: evaluation.minimum_moisture_value,
            ATTR_MAXIMUM_MOISTURE: evaluation.maximum_moisture_value,
            ATTR_REASON: evaluation.reason,
            ATTR_LAST_MODIFIED: self._runtime.last_modified,
            ATTR_LAST_WATERED: self._runtime.last_watered,
        }

        self.async_write_ha_state()


class PlantLastWateredSensor(PlantMonitorPlusEntity, SensorEntity):
    """Sensor exposing the last watered timestamp."""

    _attr_translation_key = "last_watered"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_native_value: datetime | None = None

    def __init__(self, runtime: PlantMonitorPlusRuntime) -> None:
        """Initialize the last watered sensor."""
        super().__init__(runtime)
        self._attr_unique_id = f"{runtime.entry.entry_id}_last_watered"
        self._attr_available = True

    async def async_added_to_hass(self) -> None:
        """Register listeners and evaluate initial state."""
        await super().async_added_to_hass()

        self.async_on_remove(
            self._runtime.register_moisture_callback(
                self.hass,
                self._refresh_state,
            )
        )

        self.async_on_remove(
            self._runtime.register_last_watered_callback(
                self._async_handle_last_watered_update,
            )
        )

        self._refresh_state()

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
