"""Constants for plant_monitor_plus."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "plant_monitor_plus"
MIN_HA_VERSION = "2026.5.1"

CONF_CONDUCTIVITY_ENTITY_ID = "conductivity_entity_id"
CONF_HUMIDITY_ENTITY_ID = "humidity_entity_id"
CONF_ILLUMINANCE_ENTITY_ID = "illuminance_entity_id"
CONF_MOISTURE_ENTITY_ID = "moisture_entity_id"
CONF_TEMPERATURE_ENTITY_ID = "temperature_entity_id"
