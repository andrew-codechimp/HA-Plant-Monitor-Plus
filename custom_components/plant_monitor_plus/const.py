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
CONF_WATERING_DETECTION_THRESHOLD = "watering_detection_threshold"
DEFAULT_WATERING_DETECTION_THRESHOLD = 20

SERVICE_GET_PLANT_SUMMARY = "get_plant_summary"
SERVICE_SET_PLANT_WATERED = "set_plant_watered"

SERVICE_ATTR_MOISTURE_CURRENT = "moisture_current"
SERVICE_ATTR_MOISTURE_MAXIMUM = "moisture_maximum"
SERVICE_ATTR_MOISTURE_MINIMUM = "moisture_minimum"
SERVICE_ATTR_MOISTURE_LAST_MODIFIED = "moisture_last_modified"
SERVICE_ATTR_MOISTURE_PROBLEM = "moisture_problem"
SERVICE_ATTR_MOISTURE_REASON = "moisture_reason"

ATTR_LAST_MODIFIED = "last_modified"
ATTR_LAST_WATERED = "last_watered"
ATTR_CURRENT = "current"
ATTR_MAXIMUM = "maximum"
ATTR_MINIMUM = "minimum"
ATTR_REASON = "reason"
ATTR_SOURCE_ENTITY_ID = "source_entity_id"

REASON_OK = "ok"
REASON_TOO_DRY = "too_dry"
REASON_TOO_WET = "too_wet"
REASON_THRESHOLD_DISABLED = "threshold_disabled"
REASON_ENTITY_STATE_MISSING = "entity_state_missing"
REASON_NON_NUMERIC_STATE = "non_numeric_state"

ISSUE_MOISTURE_ENTITY_INVALID = "moisture_entity_invalid"
