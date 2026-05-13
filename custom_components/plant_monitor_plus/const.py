"""Constants for plant_monitor_plus."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "plant_monitor_plus"
MIN_HA_VERSION = "2026.5.1"

CONF_MOISTURE_ENTITY_ID = "moisture_entity_id"
CONF_MOISTURE_MAX = "moisture_max"
CONF_MOISTURE_MIN = "moisture_min"

REASON_DRY = "dry"
REASON_ENTITY_NOT_CONFIGURED = "entity_not_configured"
REASON_ENTITY_STATE_MISSING = "entity_state_missing"
REASON_NON_NUMERIC_STATE = "non_numeric_state"
REASON_OK = "ok"
REASON_THRESHOLD_DISABLED = "threshold_disabled"
REASON_WET = "wet"
