"""Runtime evaluation helpers for plant_monitor_plus."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.const import CONF_NAME

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, State

from .const import (
    CONF_CONDUCTIVITY_ENTITY_ID,
    CONF_CONDUCTIVITY_MAX,
    CONF_CONDUCTIVITY_MIN,
    CONF_HUMIDITY_ENTITY_ID,
    CONF_HUMIDITY_MAX,
    CONF_HUMIDITY_MIN,
    CONF_ILLUMINANCE_ENTITY_ID,
    CONF_ILLUMINANCE_MAX,
    CONF_ILLUMINANCE_MIN,
    CONF_MOISTURE_ENTITY_ID,
    CONF_MOISTURE_MAX,
    CONF_MOISTURE_MIN,
    CONF_TEMPERATURE_ENTITY_ID,
    CONF_TEMPERATURE_MAX,
    CONF_TEMPERATURE_MIN,
)


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    """Definition of a monitored metric."""

    key: str
    label: str
    entity_key: str
    min_key: str
    max_key: str


@dataclass(frozen=True, slots=True)
class MetricEvaluation:
    """Outcome of a metric threshold evaluation."""

    available: bool
    outside: bool
    value: float | None
    min_value: float
    max_value: float
    reason: str


class PlantMonitorRuntime:
    """Shared runtime for state evaluation across entities and actions."""

    METRICS: tuple[MetricDefinition, ...] = (
        MetricDefinition(
            key="moisture",
            label="Moisture",
            entity_key=CONF_MOISTURE_ENTITY_ID,
            min_key=CONF_MOISTURE_MIN,
            max_key=CONF_MOISTURE_MAX,
        ),
        MetricDefinition(
            key="conductivity",
            label="Conductivity",
            entity_key=CONF_CONDUCTIVITY_ENTITY_ID,
            min_key=CONF_CONDUCTIVITY_MIN,
            max_key=CONF_CONDUCTIVITY_MAX,
        ),
        MetricDefinition(
            key="humidity",
            label="Humidity",
            entity_key=CONF_HUMIDITY_ENTITY_ID,
            min_key=CONF_HUMIDITY_MIN,
            max_key=CONF_HUMIDITY_MAX,
        ),
        MetricDefinition(
            key="temperature",
            label="Temperature",
            entity_key=CONF_TEMPERATURE_ENTITY_ID,
            min_key=CONF_TEMPERATURE_MIN,
            max_key=CONF_TEMPERATURE_MAX,
        ),
        MetricDefinition(
            key="illuminance",
            label="Illuminance",
            entity_key=CONF_ILLUMINANCE_ENTITY_ID,
            min_key=CONF_ILLUMINANCE_MIN,
            max_key=CONF_ILLUMINANCE_MAX,
        ),
    )

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize runtime state for an entry."""
        self.entry = entry

    @property
    def name(self) -> str:
        """Return configured plant name."""
        return str(self.entry.data.get(CONF_NAME, self.entry.title))

    def configured_metrics(self) -> list[MetricDefinition]:
        """Return metric definitions that have a configured source entity."""
        return [metric for metric in self.METRICS if self.entity_id(metric)]

    def entity_id(self, metric: MetricDefinition) -> str | None:
        """Return source entity_id for a metric."""
        entity_id = self.entry.data.get(metric.entity_key)
        return str(entity_id) if entity_id else None

    def thresholds(self, metric: MetricDefinition) -> tuple[float, float]:
        """Return (min, max) thresholds for a metric."""
        min_value = self.entry.options.get(
            metric.min_key,
            self.entry.data.get(metric.min_key, 0),
        )
        max_value = self.entry.options.get(
            metric.max_key,
            self.entry.data.get(metric.max_key, 0),
        )
        return float(min_value), float(max_value)

    def evaluate_state(
        self,
        hass: HomeAssistant,
        metric: MetricDefinition,
        state: State | None = None,
    ) -> MetricEvaluation:
        """Evaluate whether metric state is outside configured thresholds."""
        entity_id = self.entity_id(metric)
        min_value, max_value = self.thresholds(metric)

        if not entity_id:
            return MetricEvaluation(
                available=False,
                outside=False,
                value=None,
                min_value=min_value,
                max_value=max_value,
                reason="entity_not_configured",
            )

        if min_value == 0 or max_value == 0:
            return MetricEvaluation(
                available=True,
                outside=False,
                value=None,
                min_value=min_value,
                max_value=max_value,
                reason="threshold_disabled",
            )

        source_state = state if state is not None else hass.states.get(entity_id)
        if source_state is None:
            return MetricEvaluation(
                available=False,
                outside=False,
                value=None,
                min_value=min_value,
                max_value=max_value,
                reason="entity_state_missing",
            )

        try:
            value = float(source_state.state)
        except TypeError, ValueError:
            return MetricEvaluation(
                available=False,
                outside=False,
                value=None,
                min_value=min_value,
                max_value=max_value,
                reason="non_numeric_state",
            )

        outside = value < min_value or value > max_value
        return MetricEvaluation(
            available=True,
            outside=outside,
            value=value,
            min_value=min_value,
            max_value=max_value,
            reason="ok",
        )


if TYPE_CHECKING:
    PlantMonitorConfigEntry = ConfigEntry[PlantMonitorRuntime]
