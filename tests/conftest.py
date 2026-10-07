"""Fixtures for Plant Monitor Plus tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from custom_components.plant_monitor_plus.const import (
    CONF_MOISTURE_ENTITY_ID,
    CONF_MOISTURE_HIDE,
    CONF_MOISTURE_MAXIMUM,
    CONF_MOISTURE_MINIMUM,
    CONF_WATERING_DETECTION_THRESHOLD,
    DEFAULT_MOISTURE_MAX,
    DEFAULT_MOISTURE_MIN,
    DEFAULT_WATERING_DETECTION_THRESHOLD,
    DOMAIN,
)
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_NAME,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import SOURCE_ENTITY_ID


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations in Home Assistant."""


@pytest.fixture(autouse=True)
def freeze_setup_time(freezer: FrozenDateTimeFactory) -> None:
    """Keep entity timestamps and storage deadlines stable."""
    freezer.move_to("2026-07-01T12:00:00+00:00")


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Mock integration setup when testing flow data in isolation."""
    with patch(
        "custom_components.plant_monitor_plus.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_config_entry(request: pytest.FixtureRequest) -> MockConfigEntry:
    """Create a plant entry with default options and optional overrides."""
    return MockConfigEntry(
        domain=DOMAIN,
        version=1,
        entry_id="plant-entry",
        title="Monstera",
        data={CONF_NAME: "Monstera", CONF_MOISTURE_ENTITY_ID: SOURCE_ENTITY_ID},
        options={
            CONF_MOISTURE_MINIMUM: DEFAULT_MOISTURE_MIN,
            CONF_MOISTURE_MAXIMUM: DEFAULT_MOISTURE_MAX,
            CONF_WATERING_DETECTION_THRESHOLD: DEFAULT_WATERING_DETECTION_THRESHOLD,
            CONF_MOISTURE_HIDE: False,
            **getattr(request, "param", {}),
        },
    )


@pytest.fixture
def moisture_sensor(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> er.RegistryEntry:
    """Register a source moisture sensor and publish its initial state."""
    entity = entity_registry.async_get_or_create(
        "sensor",
        "test",
        "monstera-moisture",
        suggested_object_id="monstera_moisture",
        original_name="Moisture",
        original_device_class=SensorDeviceClass.MOISTURE,
        unit_of_measurement=PERCENTAGE,
    )
    hass.states.async_set(
        entity.entity_id,
        "50",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.MOISTURE,
            ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE,
        },
    )
    return entity
