"""Constants for plant_monitor_plus."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "plant_monitor_plus"
MIN_HA_VERSION = "2026.5.1"

# Config
CONF_MOISTURE_ENTITY_ID = "moisture_entity_id"
CONF_MOISTURE_MAXIMUM = "moisture_maximum"
CONF_MOISTURE_MINIMUM = "moisture_minimum"
CONF_WATERING_DETECTION_THRESHOLD = "watering_detection_threshold"

# Defaults
DEFAULT_MOISTURE_MIN = 30
DEFAULT_MOISTURE_MAX = 70
DEFAULT_WATERING_DETECTION_THRESHOLD = 5
WATERING_DETECTION_WINDOW_MINUTES = 60

# Services
SERVICE_GET_PLANT_SUMMARY = "get_plant_summary"
SERVICE_SET_PLANT_WATERED = "set_plant_watered"
SERVICE_SET_PLANT_THRESHOLDS = "set_plant_thresholds"

# Service parameters
SERVICE_PARAM_DATETIME = "datetime"
SERVICE_PARAM_MOISTURE_MINIMUM = "moisture_minimum"
SERVICE_PARAM_MOISTURE_MAXIMUM = "moisture_maximum"

# Service response attributes
SERVICE_ATTR_MOISTURE_CURRENT = "moisture_current"
SERVICE_ATTR_MOISTURE_MAXIMUM = "moisture_maximum"
SERVICE_ATTR_MOISTURE_MINIMUM = "moisture_minimum"
SERVICE_ATTR_MOISTURE_PROBLEM_LAST_MODIFIED = "moisture_problem_last_modified"
SERVICE_ATTR_MOISTURE_PROBLEM = "moisture_problem"
SERVICE_ATTR_MOISTURE_REASON = "moisture_reason"
SERVICE_ATTR_UNAVAILABLE = "unavailable"
SERVICE_ATTR_PLANTS = "plants"

# Entity attributes
ATTR_PROBLEM_LAST_MODIFIED = "problem_last_modified"
ATTR_LAST_WATERED = "last_watered"
ATTR_CURRENT = "current"
ATTR_MAXIMUM = "maximum"
ATTR_MINIMUM = "minimum"
ATTR_REASON = "reason"
ATTR_SOURCE_ENTITY_ID = "source_entity_id"

# Storage fields
REMOVE = "remove"
MOISTURE_PROBLEM_LAST_MODIFIED = "moisture_problem_last_modified"
MOISTURE_PROBLEM_STATE = "moisture_problem_state"
LAST_WATERED = "last_watered"

# Moisture problem reasons
REASON_OK = "ok"
REASON_TOO_DRY = "too_dry"
REASON_TOO_WET = "too_wet"
REASON_THRESHOLD_DISABLED = "threshold_disabled"
REASON_ENTITY_STATE_MISSING = "entity_state_missing"
REASON_NON_NUMERIC_STATE = "non_numeric_state"

# Issues
ISSUE_MOISTURE_ENTITY_INVALID = "moisture_entity_invalid"
