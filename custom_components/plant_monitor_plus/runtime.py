"""Runtime evaluation helpers for plant_monitor_plus."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypedDict, cast

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.helpers.event import (
    async_track_entity_registry_updated_event,
    async_track_state_change_event,
)
from homeassistant.util import dt as dt_util

from .const import (
    CONF_MOISTURE_ENTITY_ID,
    CONF_MOISTURE_MAX,
    CONF_MOISTURE_MIN,
    CONF_WATERING_DETECTION_THRESHOLD,
    DOMAIN,
    ISSUE_MOISTURE_ENTITY_INVALID,
    REASON_DRY,
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
    from homeassistant.core import Event, EventStateChangedData, State

    from .store import PlantMonitorStore


class _RegistryEntityUpdatedData(TypedDict):
    """Typed payload for entity registry update events."""

    action: Literal["update"]
    entity_id: str
    changes: dict[str, Any]


@dataclass(frozen=True, slots=True)
class MoistureEvaluation:
    """Outcome of a moisture threshold evaluation."""

    available: bool
    outside: bool
    moisture_value: float | None
    minimum_moisture_value: float
    maximum_moisture_value: float
    reason: str


class PlantMonitorPlusRuntime:
    """Shared runtime for state evaluation across entities and actions."""

    def __init__(self, entry: ConfigEntry, store: PlantMonitorStore) -> None:
        """Initialize runtime state for an entry."""
        self.entry = entry
        self._store = store
        self._previous_moisture_value: float | None = None
        self._last_watered_callbacks: list[Callable[[], None]] = []
        self._moisture_callbacks: list[Callable[[State | None], None]] = []
        self._moisture_unsubscribe: Callable[[], None] | None = None
        self._hass: HomeAssistant | None = None
        self._registry_unsubscribe: Callable[[], None] | None = None
        self._tracked_moisture_entity_id: str | None = None

    @property
    def _moisture_entity_issue_id(self) -> str:
        """Return issue id for moisture source problems."""
        return f"{ISSUE_MOISTURE_ENTITY_INVALID}_{self.entry.entry_id}"

    @property
    def name(self) -> str:
        """Return configured plant name."""
        return str(self.entry.data.get(CONF_NAME, self.entry.title))

    @property
    def last_watered(self) -> datetime | None:
        """Return the last watering timestamp."""
        return self._store.last_watered(self.entry.entry_id)

    @property
    def last_modified(self) -> datetime | None:
        """Return the last problem state modification timestamp."""
        return self._store.last_modified(self.entry.entry_id)

    @property
    def has_problem_state(self) -> bool:
        """Return whether a previous problem state is persisted."""
        return self._store.has_problem_state(self.entry.entry_id)

    @property
    def problem_state(self) -> bool | None:
        """Return the persisted problem state."""
        return self._store.problem_state(self.entry.entry_id)

    @property
    def moisture_entity_id(self) -> str:
        """Return the configured moisture sensor entity_id."""
        entity_id = self.entry.data[CONF_MOISTURE_ENTITY_ID]
        return str(entity_id)

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

        source_state = state if state is not None else hass.states.get(entity_id)
        if source_state is None:
            return MoistureEvaluation(
                available=False,
                outside=False,
                moisture_value=None,
                minimum_moisture_value=min_value,
                maximum_moisture_value=max_value,
                reason=REASON_ENTITY_STATE_MISSING,
            )

        try:
            value = float(source_state.state)
        except TypeError, ValueError:
            return MoistureEvaluation(
                available=False,
                outside=False,
                moisture_value=None,
                minimum_moisture_value=min_value,
                maximum_moisture_value=max_value,
                reason=REASON_NON_NUMERIC_STATE,
            )

        if min_value == 0 or max_value == 0:
            return MoistureEvaluation(
                available=True,
                outside=False,
                moisture_value=value,
                minimum_moisture_value=min_value,
                maximum_moisture_value=max_value,
                reason=REASON_THRESHOLD_DISABLED,
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
            moisture_value=value,
            minimum_moisture_value=min_value,
            maximum_moisture_value=max_value,
            reason=reason,
        )

    def record_moisture_reading(self, value: float | None) -> None:
        """Update last watered when moisture increases significantly."""
        if value is None:
            return

        threshold = float(self.entry.options[CONF_WATERING_DETECTION_THRESHOLD])
        if threshold == 0:
            return

        previous_value = self._previous_moisture_value
        self._previous_moisture_value = value

        if previous_value is None:
            return

        increased_significantly = (value - previous_value) >= threshold

        if increased_significantly:
            self.mark_watered_now()

    async def async_set_last_watered(self, dt: datetime) -> None:
        """Set the last watered timestamp and notify listeners."""
        self._store.update_last_watered(self.entry.entry_id, dt)
        for cb in tuple(self._last_watered_callbacks):
            cb()

    def mark_watered_now(self) -> None:
        """Set last watered to current time and notify listeners."""
        self._store.update_last_watered(self.entry.entry_id, dt_util.utcnow())
        for cb in tuple(self._last_watered_callbacks):
            cb()

    def mark_modified_now(self) -> None:
        """Set last modified to current time."""
        self._store.update_last_modified(self.entry.entry_id, dt_util.utcnow())

    def set_problem_state(self, state: bool | None) -> None:
        """Persist the latest problem state."""
        self._store.update_problem_state(self.entry.entry_id, state)

    def register_moisture_callback(
        self,
        hass: HomeAssistant,
        callback: Callable[[State | None], None],
    ) -> Callable[[], None]:
        """Register callback fired when the configured moisture entity changes."""
        self._moisture_callbacks.append(callback)

        if self._moisture_unsubscribe is None:
            self._moisture_unsubscribe = async_track_state_change_event(
                hass,
                [self.moisture_entity_id],
                self._async_handle_moisture_state_change,
            )

        def unsubscribe() -> None:
            if callback in self._moisture_callbacks:
                self._moisture_callbacks.remove(callback)

            if not self._moisture_callbacks and self._moisture_unsubscribe is not None:
                self._moisture_unsubscribe()
                self._moisture_unsubscribe = None

        return unsubscribe

    @callback
    def _async_handle_moisture_state_change(
        self,
        event: Event[EventStateChangedData],
    ) -> None:
        """Dispatch moisture source updates to runtime subscribers."""
        new_state = event.data.get("new_state")
        for cb in tuple(self._moisture_callbacks):
            cb(new_state)

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

    @callback
    def async_setup_moisture_entity_watcher(
        self, hass: HomeAssistant
    ) -> Callable[[], None]:
        """Watch source moisture entity for registry rename/removal events."""
        self._hass = hass
        self._async_update_registry_watcher(hass, self.moisture_entity_id)
        self._async_clear_or_create_missing_entity_issue(hass)

        @callback
        def _cleanup() -> None:
            if self._registry_unsubscribe is not None:
                self._registry_unsubscribe()
                self._registry_unsubscribe = None

        return _cleanup

    @callback
    def _async_update_registry_watcher(
        self,
        hass: HomeAssistant,
        entity_id: str,
    ) -> None:
        """Recreate watcher for the current moisture entity id."""
        if self._registry_unsubscribe is not None:
            self._registry_unsubscribe()
            self._registry_unsubscribe = None

        self._tracked_moisture_entity_id = entity_id
        self._registry_unsubscribe = async_track_entity_registry_updated_event(
            hass,
            entity_id,
            self._async_handle_moisture_entity_registry_change,
        )

    @callback
    def _async_clear_or_create_missing_entity_issue(self, hass: HomeAssistant) -> None:
        """Create issue if source entity no longer exists in registry."""
        entity_id = self.moisture_entity_id
        if er.async_get(hass).async_get(entity_id) is not None:
            ir.async_delete_issue(hass, DOMAIN, self._moisture_entity_issue_id)
            return

        self._async_create_moisture_entity_issue(
            hass,
            translation_key="moisture_entity_removed",
            placeholders={"entity_id": entity_id, "name": self.name},
        )

    @callback
    def _async_handle_moisture_entity_registry_change(
        self,
        event: Event[er.EventEntityRegistryUpdatedData],
    ) -> None:
        """Handle source moisture entity rename/removal events."""
        if self._hass is None:
            return

        data = event.data
        action = data["action"]

        if action == "remove":
            self._async_create_moisture_entity_issue(
                self._hass,
                translation_key="moisture_entity_removed",
                placeholders={"entity_id": data["entity_id"], "name": self.name},
            )
            return

        if action != "update":
            return

        update_data = cast(_RegistryEntityUpdatedData, data)
        changes = update_data["changes"]
        if "entity_id" not in changes:
            return

        new_entity_id = data["entity_id"]

        # Entity rename: keep config in sync and reload silently.
        self._hass.config_entries.async_update_entry(
            self.entry,
            data={
                **self.entry.data,
                CONF_MOISTURE_ENTITY_ID: new_entity_id,
            },
        )
        self._async_update_registry_watcher(self._hass, new_entity_id)
        ir.async_delete_issue(self._hass, DOMAIN, self._moisture_entity_issue_id)
        self._hass.config_entries.async_schedule_reload(self.entry.entry_id)

    @callback
    def _async_create_moisture_entity_issue(
        self,
        hass: HomeAssistant,
        *,
        translation_key: str,
        placeholders: dict[str, str],
    ) -> None:
        """Create a fixable issue that starts reconfigure for this entry."""
        ir.async_create_issue(
            hass,
            DOMAIN,
            self._moisture_entity_issue_id,
            is_fixable=True,
            is_persistent=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key=translation_key,
            translation_placeholders=placeholders,
            data={"entry_id": self.entry.entry_id},
        )


if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    PlantMonitorPlusConfigEntry = ConfigEntry[PlantMonitorPlusRuntime]
