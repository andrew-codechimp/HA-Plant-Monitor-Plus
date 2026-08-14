"""Binary sensors for plant_monitor_plus threshold problems."""

from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import callback

from .const import (
    ATTR_CURRENT,
    ATTR_LAST_WATERED,
    ATTR_LAST_WATERED_DAYS,
    ATTR_MAXIMUM,
    ATTR_MINIMUM,
    ATTR_PROBLEM_LAST_MODIFIED,
    ATTR_REASON,
    ATTR_SOURCE_ENTITY_ID,
    REASON_THRESHOLD_DISABLED,
)
from .entity import PlantMonitorPlusEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, State
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .runtime import PlantMonitorPlusConfigEntry, PlantMonitorPlusRuntime


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: PlantMonitorPlusConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up plant moisture problem sensor for a config entry."""
    runtime: PlantMonitorPlusRuntime = entry.runtime_data
    entity_description = BinarySensorEntityDescription(
        key="moisture_status",
        translation_key="moisture_status",
        device_class=BinarySensorDeviceClass.PROBLEM,
    )
    async_add_entities([PlantMoistureProblemBinarySensor(entity_description, runtime)])


class PlantMoistureProblemBinarySensor(PlantMonitorPlusEntity, BinarySensorEntity):
    """Binary sensor that reports whether moisture is outside its thresholds."""

    def __init__(
        self,
        entity_description: BinarySensorEntityDescription,
        runtime: PlantMonitorPlusRuntime,
    ) -> None:
        """Initialize the moisture problem binary sensor."""
        super().__init__(runtime, entity_description.key)
        self.entity_description = entity_description

        self._attr_is_on = False
        self._attr_available = True
        self._attr_extra_state_attributes: dict[str, Any] = {}

    async def async_added_to_hass(self) -> None:
        """Register state listener and evaluate the initial state."""
        await super().async_added_to_hass()

        self.async_on_remove(
            self._runtime.register_moisture_callback(
                self.hass,
                self._refresh_state,
            )
        )

        # Register callback for last_watered updates
        self.async_on_remove(
            self._runtime.register_last_watered_callback(
                self._async_last_watered_updated
            )
        )

        self._refresh_state()

    @callback
    def _async_last_watered_updated(self) -> None:
        """Handle last watered timestamp updates."""
        self._attr_extra_state_attributes[ATTR_LAST_WATERED] = (
            self._runtime.last_watered
        )
        self.async_write_ha_state()

    @callback
    def _refresh_state(self, source_state: State | None = None) -> None:
        """Re-evaluate sensor state from current moisture value and thresholds."""
        evaluation = self._runtime.evaluate_moisture(
            hass=self.hass,
            state=source_state,
        )

        previous_state = self._runtime.moisture_problem_state
        self._attr_available = evaluation.available

        # Only treat available evaluations as authoritative for change tracking.
        if evaluation.available:
            current_problem_state: bool | None = (
                None
                if evaluation.reason == REASON_THRESHOLD_DISABLED
                else evaluation.problem
            )
            self._attr_is_on = current_problem_state

            if previous_state is not None and current_problem_state != previous_state:
                self._runtime.set_moisture_problem_modified_now()

            self._runtime.set_moisture_problem_state(current_problem_state)

        self._attr_extra_state_attributes = {
            ATTR_SOURCE_ENTITY_ID: self._runtime.moisture_entity_id,
            ATTR_CURRENT: evaluation.value,
            ATTR_MINIMUM: evaluation.minimum_value,
            ATTR_MAXIMUM: evaluation.maximum_value,
            ATTR_REASON: evaluation.reason,
            ATTR_PROBLEM_LAST_MODIFIED: self._runtime.moisture_problem_last_modified,
            ATTR_LAST_WATERED: self._runtime.last_watered,
            ATTR_LAST_WATERED_DAYS: self._runtime.last_watered_days,
        }

        self.async_write_ha_state()
