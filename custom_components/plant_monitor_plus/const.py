"""Constants for plant_monitor_plus."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "plant_monitor_plus"
MIN_HA_VERSION = "2026.5.1"
STORE_KEY = f"{DOMAIN}_last_watered"
STORE_VERSION = 1

CONF_MOISTURE_ENTITY_ID = "moisture_entity_id"
CONF_MOISTURE_MAX = "moisture_max"
CONF_MOISTURE_MIN = "moisture_min"
CONF_MOISTURE_WATERING_INCREASE = "moisture_watering_increase"
DEFAULT_MOISTURE_WATERING_INCREASE = 20

SERVICE_GET_PLANT_SUMMARY = "get_plant_summary"
SERVICE_SET_PLANT_WATERED = "set_plant_watered"

ATTR_CURRENT = "current"
ATTR_LAST_WATERED = "last_watered"
ATTR_MAX = "max"
ATTR_MIN = "min"
ATTR_REASON = "reason"
ATTR_SOURCE_ENTITY_ID = "source_entity_id"

REASON_DRY = "dry"
REASON_ENTITY_STATE_MISSING = "entity_state_missing"
REASON_NON_NUMERIC_STATE = "non_numeric_state"
REASON_OK = "ok"
REASON_THRESHOLD_DISABLED = "threshold_disabled"
REASON_WET = "wet"

ISSUE_MOISTURE_ENTITY_INVALID = "moisture_entity_invalid"
