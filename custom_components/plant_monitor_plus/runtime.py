"""Runtime evaluation helpers for plant_monitor_plus."""

from collections import deque
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Literal, TypedDict, cast

from homeassistant.const import CONF_NAME, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.helpers.event import (
    async_track_entity_registry_updated_event,
    async_track_state_change_event,
)
from homeassistant.util import dt as dt_util

from .const import (
    CONF_MOISTURE_ENTITY_ID,
    CONF_MOISTURE_MAXIMUM,
    CONF_MOISTURE_MINIMUM,
    CONF_WATERING_DETECTION_THRESHOLD,
    DOMAIN,
    ISSUE_MOISTURE_ENTITY_INVALID,
    LAST_WATERED,
    MIN_READINGS_FOR_DETECTION,
    MOISTURE_LAST_VALUE,
    MOISTURE_PROBLEM_LAST_MODIFIED,
    MOISTURE_PROBLEM_STATE,
    REASON_ENTITY_STATE_MISSING,
    REASON_NON_NUMERIC_STATE,
    REASON_OK,
    REASON_THRESHOLD_DISABLED,
    REASON_TOO_DRY,
    REASON_TOO_WET,
    REMOVE,
    THRESHOLD_DISABLED_VALUE,
    WATERING_DETECTION_WINDOW_MINUTES,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import Event, EventStateChangedData, State

    from .store import PlantMonitorStorage


class _RegistryEntityUpdatedData(TypedDict):
    """Typed payload for entity registry update events."""

    action: Literal["update"]
    entity_id: str
    changes: dict[str, Any]


@dataclass(frozen=True, slots=True)
class MoistureEvaluation:
    """Outcome of a moisture threshold evaluation."""

    available: bool
    problem: bool
    value: float | None
    minimum_value: float
    maximum_value: float
    reason: str


class PlantMonitorPlusRuntime:
    """Shared runtime for state evaluation across entities and actions."""

    def __init__(self, entry: ConfigEntry, store: PlantMonitorStorage) -> None:
        """Initialize runtime state for an entry."""
        self.entry = entry
        self._store = store
        self._recent_moisture_readings: deque[tuple[datetime, float]] = deque()
        self._last_watered_callbacks: list[Callable[[], None]] = []
        self._moisture_callbacks: list[Callable[[State | None], None]] = []
        self._moisture_unsubscribe: Callable[[], None] | None = None
        self._hass: HomeAssistant | None = None
        self._registry_unsubscribe: Callable[[], None] | None = None
        self._tracked_moisture_entity_id: str | None = None

    def async_update_device(self, device_id: str, data: dict) -> None:
        """Conditional create, update or remove device from store."""

        if REMOVE in data:
            self._store.async_delete_device(device_id)
        elif self._store.async_get_device(device_id):
            self._store.async_update_device(device_id, data)
        else:
            self._store.async_create_device(device_id, data)

    def restore_recent_moisture_readings(self) -> None:
        """Pre-populate recent moisture readings with the last known value to enable watering detection on startup."""
        entry = self._store.async_get_device(self.entry.entry_id)

        if (
            entry
            and MOISTURE_LAST_VALUE in entry
            and entry[MOISTURE_LAST_VALUE] is not None
        ):
            last_value = entry[MOISTURE_LAST_VALUE]
            now = dt_util.utcnow()
            self._recent_moisture_readings.append((now, float(last_value)))

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
        entry = self._store.async_get_device(self.entry.entry_id)

        if entry and LAST_WATERED in entry and entry[LAST_WATERED] is not None:
            last_watered = entry[LAST_WATERED]
            if isinstance(last_watered, str):
                return dt_util.parse_datetime(last_watered)
            return cast("datetime", last_watered)
        return None

    @property
    def last_watered_days(self) -> int | None:
        """Return the number of days since last watered."""
        if self.last_watered is None:
            return None
        delta = dt_util.utcnow() - self.last_watered
        return delta.days

    @property
    def moisture_problem_last_modified(self) -> datetime | None:
        """Return the last problem state modification timestamp."""
        entry = self._store.async_get_device(self.entry.entry_id)

        if (
            entry
            and MOISTURE_PROBLEM_LAST_MODIFIED in entry
            and entry[MOISTURE_PROBLEM_LAST_MODIFIED] is not None
        ):
            modified = entry[MOISTURE_PROBLEM_LAST_MODIFIED]
            if isinstance(modified, str):
                return dt_util.parse_datetime(modified)
            return cast("datetime", modified)
        return None

    @property
    def moisture_problem_state(self) -> bool | None:
        """Return the persisted moisture problem state."""
        entry = self._store.async_get_device(self.entry.entry_id)

        if (
            entry
            and MOISTURE_PROBLEM_STATE in entry
            and entry[MOISTURE_PROBLEM_STATE] is not None
        ):
            return entry[MOISTURE_PROBLEM_STATE]
        return None

    @property
    def moisture_entity_id(self) -> str:
        """Return the configured moisture sensor entity_id."""
        entity_id = self.entry.data[CONF_MOISTURE_ENTITY_ID]
        return str(entity_id)

    @property
    def moisture_thresholds(self) -> tuple[float, float]:
        """Return (min, max) moisture thresholds."""
        min_value = self.entry.options[CONF_MOISTURE_MINIMUM]
        max_value = self.entry.options[CONF_MOISTURE_MAXIMUM]
        return float(min_value), float(max_value)

    def evaluate_moisture(
        self,
        hass: HomeAssistant,
        state: State | None = None,
    ) -> MoistureEvaluation:
        """Evaluate whether moisture is outside configured thresholds."""
        entity_id = self.moisture_entity_id
        minimum_value, maximum_value = self.moisture_thresholds

        source_state = state if state is not None else hass.states.get(entity_id)
        if source_state is None or source_state.state in (
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
        ):
            return MoistureEvaluation(
                available=False,
                problem=False,
                value=None,
                minimum_value=minimum_value,
                maximum_value=maximum_value,
                reason=REASON_ENTITY_STATE_MISSING,
            )

        try:
            value = float(source_state.state)
        except TypeError, ValueError:
            return MoistureEvaluation(
                available=False,
                problem=False,
                value=None,
                minimum_value=minimum_value,
                maximum_value=maximum_value,
                reason=REASON_NON_NUMERIC_STATE,
            )

        if THRESHOLD_DISABLED_VALUE in (minimum_value, maximum_value):
            return MoistureEvaluation(
                available=True,
                problem=False,
                value=value,
                minimum_value=minimum_value,
                maximum_value=maximum_value,
                reason=REASON_THRESHOLD_DISABLED,
            )

        if value < minimum_value:
            reason = REASON_TOO_DRY
        elif value > maximum_value:
            reason = REASON_TOO_WET
        else:
            reason = REASON_OK
        return MoistureEvaluation(
            available=True,
            problem=reason != REASON_OK,
            value=value,
            minimum_value=minimum_value,
            maximum_value=maximum_value,
            reason=reason,
        )

    def record_moisture_reading(self, value: float | None) -> None:
        """Update last watered when moisture increases within the detection window."""
        if value is None:
            return

        threshold = float(self.entry.options[CONF_WATERING_DETECTION_THRESHOLD])
        if threshold == THRESHOLD_DISABLED_VALUE:
            return

        now = dt_util.utcnow()
        self._recent_moisture_readings.append((now, value))

        device = {MOISTURE_LAST_VALUE: value}
        self.async_update_device(device_id=self.entry.entry_id, data=device)

        window_start = now - timedelta(minutes=WATERING_DETECTION_WINDOW_MINUTES)
        while (
            len(self._recent_moisture_readings) > MIN_READINGS_FOR_DETECTION
            and self._recent_moisture_readings[0][0] < window_start
        ):
            self._recent_moisture_readings.popleft()

        if len(self._recent_moisture_readings) < MIN_READINGS_FOR_DETECTION:
            return

        lowest_window_value = min(
            reading_value for _, reading_value in self._recent_moisture_readings
        )
        increased_significantly = (value - lowest_window_value) >= threshold

        if increased_significantly:
            self.set_watered_now()
            # Reset baseline after detection to avoid repeated triggers on the same rise.
            self._recent_moisture_readings.clear()
            self._recent_moisture_readings.append((now, value))

    async def async_set_last_watered(self, dt: datetime) -> None:
        """Set the last watered timestamp and notify listeners."""
        device = {LAST_WATERED: dt}
        self.async_update_device(device_id=self.entry.entry_id, data=device)
        for cb in tuple(self._last_watered_callbacks):
            cb()

    def set_watered_now(self) -> None:
        """Set last watered to current time and notify listeners."""
        device = {LAST_WATERED: dt_util.utcnow()}
        self.async_update_device(device_id=self.entry.entry_id, data=device)
        for cb in tuple(self._last_watered_callbacks):
            cb()

    def set_moisture_problem_modified_now(self) -> None:
        """Set last moisture modified problem to current time."""
        device = {MOISTURE_PROBLEM_LAST_MODIFIED: dt_util.utcnow()}
        self.async_update_device(device_id=self.entry.entry_id, data=device)

    def set_moisture_problem_state(self, state: bool | None) -> None:
        """Persist the latest moisture problem state."""
        if self.moisture_problem_state != state:
            device = {MOISTURE_PROBLEM_STATE: state}
            self.async_update_device(device_id=self.entry.entry_id, data=device)

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

        value: float | None = None
        if new_state is not None:
            try:
                value = float(new_state.state)
            except TypeError, ValueError:
                value = None

        self.record_moisture_reading(value)

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
        """Create an issue."""
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
