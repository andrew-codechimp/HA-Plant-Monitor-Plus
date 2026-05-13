"""Runtime evaluation helpers for plant_monitor_plus."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.const import CONF_NAME

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, State

from .const import (
    CONF_MOISTURE_ENTITY_ID,
    CONF_MOISTURE_MAX,
    CONF_MOISTURE_MIN,
    REASON_DRY,
    REASON_ENTITY_NOT_CONFIGURED,
    REASON_ENTITY_STATE_MISSING,
    REASON_NON_NUMERIC_STATE,
    REASON_OK,
    REASON_THRESHOLD_DISABLED,
    REASON_WET,
)


@dataclass(frozen=True, slots=True)
class MoistureEvaluation:
    """Outcome of a moisture threshold evaluation."""

    available: bool
    outside: bool
    value: float | None
    min_value: float
    max_value: float
    reason: str


class PlantMonitorRuntime:
    """Shared runtime for state evaluation across entities and actions."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize runtime state for an entry."""
        self.entry = entry

    @property
    def name(self) -> str:
        """Return configured plant name."""
        return str(self.entry.data.get(CONF_NAME, self.entry.title))

    @property
    def moisture_entity_id(self) -> str | None:
        """Return the configured moisture sensor entity_id."""
        entity_id = self.entry.data.get(CONF_MOISTURE_ENTITY_ID)
        return str(entity_id) if entity_id else None

    @property
    def moisture_thresholds(self) -> tuple[float, float]:
        """Return (min, max) moisture thresholds."""
        min_value = self.entry.options.get(
            CONF_MOISTURE_MIN,
            self.entry.data.get(CONF_MOISTURE_MIN, 0),
        )
        max_value = self.entry.options.get(
            CONF_MOISTURE_MAX,
            self.entry.data.get(CONF_MOISTURE_MAX, 0),
        )
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


if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    PlantMonitorConfigEntry = ConfigEntry[PlantMonitorRuntime]
