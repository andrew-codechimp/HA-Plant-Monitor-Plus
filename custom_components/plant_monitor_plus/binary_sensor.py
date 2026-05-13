"""Binary sensors for plant_monitor_plus threshold problems."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .runtime import MetricDefinition, PlantMonitorConfigEntry, PlantMonitorRuntime


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: PlantMonitorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up plant metric problem sensors for a config entry."""
    runtime: PlantMonitorRuntime = entry.runtime_data

    entities = [
        PlantMetricProblemBinarySensor(runtime=runtime, metric=metric)
        for metric in runtime.configured_metrics()
    ]
    async_add_entities(entities)


class PlantMetricProblemBinarySensor(BinarySensorEntity):
    """Binary sensor that reports whether a metric is outside its thresholds."""

    _attr_should_poll = False

    def __init__(self, runtime: PlantMonitorRuntime, metric: MetricDefinition) -> None:
        """Initialize the problem binary sensor."""
        self._runtime = runtime
        self._metric = metric
        self._attr_name = f"{runtime.name} {metric.label} Problem"
        self._attr_unique_id = f"{runtime.entry.entry_id}_{metric.key}_problem"
        self._attr_is_on = False
        self._attr_available = True
        self._attr_extra_state_attributes: dict[str, Any] = {
            "metric": metric.key,
        }

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info for this sensor."""
        return {
            "identifiers": {(DOMAIN, self._runtime.entry.entry_id)},
            "name": self._runtime.name,
        }

    async def async_added_to_hass(self) -> None:
        """Register state listeners and evaluate the initial state."""
        await super().async_added_to_hass()

        entity_id = self._runtime.entity_id(self._metric)
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
        """Re-evaluate sensor state from current source value and thresholds."""
        evaluation = self._runtime.evaluate_state(
            hass=self.hass,
            metric=self._metric,
            state=source_state,
        )

        self._attr_available = evaluation.available
        self._attr_is_on = evaluation.outside
        self._attr_extra_state_attributes = {
            "metric": self._metric.key,
            "source_entity_id": self._runtime.entity_id(self._metric),
            "current": evaluation.value,
            "min": evaluation.min_value,
            "max": evaluation.max_value,
            "reason": evaluation.reason,
        }
        self.async_write_ha_state()
