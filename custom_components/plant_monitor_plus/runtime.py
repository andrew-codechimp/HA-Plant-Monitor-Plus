"""Runtime evaluation helpers for plant_monitor_plus."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.const import CONF_NAME
from homeassistant.util import dt as dt_util

from .const import (
    CONF_MOISTURE_ENTITY_ID,
    CONF_MOISTURE_MAX,
    CONF_MOISTURE_MIN,
    CONF_MOISTURE_WATERING_INCREASE,
    REASON_DRY,
    REASON_ENTITY_NOT_CONFIGURED,
    REASON_ENTITY_STATE_MISSING,
    REASON_NON_NUMERIC_STATE,
    REASON_OK,
    REASON_THRESHOLD_DISABLED,
    REASON_WET,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, State

    from .store import PlantMonitorStore


@dataclass(frozen=True, slots=True)
class MoistureEvaluation:
    """Outcome of a moisture threshold evaluation."""

    available: bool
    outside: bool
    value: float | None
    min_value: float
    max_value: float
    reason: str


class PlantMonitorPlusRuntime:
    """Shared runtime for state evaluation across entities and actions."""

    def __init__(self, entry: ConfigEntry, store: PlantMonitorStore) -> None:
        """Initialize runtime state for an entry."""
        self.entry = entry
        self._store = store
        self._previous_moisture_value: float | None = None
        self._last_watered_callbacks: list[Callable[[], None]] = []

    @property
    def name(self) -> str:
        """Return configured plant name."""
        return str(self.entry.data.get(CONF_NAME, self.entry.title))

    @property
    def last_watered(self) -> datetime | None:
        """Return the last watering timestamp."""
        return self._store.last_watered(self.entry.entry_id)

    @property
    def moisture_entity_id(self) -> str | None:
        """Return the configured moisture sensor entity_id."""
        entity_id = self.entry.data[CONF_MOISTURE_ENTITY_ID]
        return str(entity_id) if entity_id else None

    @property
    def moisture_thresholds(self) -> tuple[float, float]:
        """Return (min, max) moisture thresholds."""
        min_value = self.entry.options[CONF_MOISTURE_MIN]
        max_value = self.entry.options[CONF_MOISTURE_MAX]
        return float(min_value), float(max_value)

    def evaluate_moisture(
        self,
        hass: HomeAssistant,
        state: State | None = None,
    ) -> MoistureEvaluation:
        """Evaluate whether moisture is outside configured thresholds."""
        entity_id = self.moisture_entity_id
        min_value, max_value = self.moisture_thresholds

        if not entity_id:
            return MoistureEvaluation(
                available=False,
                outside=False,
                value=None,
                min_value=min_value,
                max_value=max_value,
                reason=REASON_ENTITY_NOT_CONFIGURED,
            )

        if min_value == 0 or max_value == 0:
            return MoistureEvaluation(
                available=True,
                outside=False,
                value=None,
                min_value=min_value,
                max_value=max_value,
                reason=REASON_THRESHOLD_DISABLED,
            )

        source_state = state if state is not None else hass.states.get(entity_id)
        if source_state is None:
            return MoistureEvaluation(
                available=False,
                outside=False,
                value=None,
                min_value=min_value,
                max_value=max_value,
                reason=REASON_ENTITY_STATE_MISSING,
            )

        try:
            value = float(source_state.state)
        except TypeError, ValueError:
            return MoistureEvaluation(
                available=False,
                outside=False,
                value=None,
                min_value=min_value,
                max_value=max_value,
                reason=REASON_NON_NUMERIC_STATE,
            )

        if value < min_value:
            reason = REASON_DRY
        elif value > max_value:
            reason = REASON_WET
        else:
            reason = REASON_OK
        return MoistureEvaluation(
            available=True,
            outside=reason != REASON_OK,
            value=value,
            min_value=min_value,
            max_value=max_value,
            reason=reason,
        )

    def record_moisture_reading(self, value: float | None) -> None:
        """Update last watered when moisture increases significantly."""
        if value is None:
            return

        threshold = float(self.entry.options[CONF_MOISTURE_WATERING_INCREASE])
        if threshold == 0:
            return

        previous_value = self._previous_moisture_value
        self._previous_moisture_value = value

        if previous_value is None:
            return

        if previous_value <= 0:
            increased_significantly = value > previous_value
        else:
            increased_significantly = (value - previous_value) >= previous_value * (
                threshold / 100.0
            )

        if not increased_significantly:
            return

        self.mark_watered_now()

    def mark_watered_now(self) -> None:
        """Mark this plant as watered at the current UTC timestamp."""
        self._store.async_update_last_watered(self.entry.entry_id, dt_util.utcnow())
        for callback in tuple(self._last_watered_callbacks):
            callback()

    def set_last_watered(self, dt: datetime) -> None:
        """Set the last watered timestamp and notify listeners."""
        self._store.async_update_last_watered(self.entry.entry_id, dt)
        for callback in tuple(self._last_watered_callbacks):
            callback()

    def register_last_watered_callback(
        self,
        callback: Callable[[], None],
    ) -> Callable[[], None]:
        """Register callback fired when last watered is updated."""
        self._last_watered_callbacks.append(callback)

        def unsubscribe() -> None:
            if callback in self._last_watered_callbacks:
                self._last_watered_callbacks.remove(callback)

        return unsubscribe


if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    PlantMonitorConfigEntry = ConfigEntry[PlantMonitorPlusRuntime]
