"""Constants for plant_monitor_plus."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "plant_monitor_plus"
MIN_HA_VERSION = "2026.5.1"

CONF_MANUFACTURER = "manufacturer"
CONF_MOISTURE_ENTITY_ID = "moisture_entity_id"
CONF_MODEL = "model"
CONF_SERIAL_NUMBER = "serial_number"
