"""Service registration for plant_monitor_plus."""

from functools import partial
from typing import TYPE_CHECKING, cast

import voluptuous as vol

from homeassistant.const import ATTR_CONFIG_ENTRY_ID, ATTR_NAME
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    selector,
    service,
)
from homeassistant.util import dt as dt_util

from .const import (
    CONF_MOISTURE_MAXIMUM,
    CONF_MOISTURE_MINIMUM,
    DOMAIN,
    REASON_TOO_DRY,
    REASON_TOO_WET,
    SERVICE_ATTR_DEVICE_ID,
    SERVICE_ATTR_LAST_WATERED,
    SERVICE_ATTR_LAST_WATERED_DAYS,
    SERVICE_ATTR_MOISTURE_CURRENT,
    SERVICE_ATTR_MOISTURE_MAXIMUM,
    SERVICE_ATTR_MOISTURE_MINIMUM,
    SERVICE_ATTR_MOISTURE_PROBLEM,
    SERVICE_ATTR_MOISTURE_PROBLEM_LAST_MODIFIED,
    SERVICE_ATTR_MOISTURE_REASON,
    SERVICE_ATTR_PLANTS,
    SERVICE_ATTR_UNAVAILABLE,
    SERVICE_GET_PLANT_SUMMARY,
    SERVICE_PARAM_DATETIME,
    SERVICE_PARAM_MOISTURE_MAXIMUM,
    SERVICE_PARAM_MOISTURE_MINIMUM,
    SERVICE_SET_PLANT_THRESHOLDS,
    SERVICE_SET_PLANT_WATERED,
)

if TYPE_CHECKING:
    from custom_components.plant_monitor_plus.runtime import PlantMonitorPlusRuntime

    from .runtime import PlantMonitorPlusConfigEntry

SERVICE_SET_PLANT_THRESHOLDS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional(SERVICE_PARAM_MOISTURE_MINIMUM): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
            )
        ),
        vol.Optional(SERVICE_PARAM_MOISTURE_MAXIMUM): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=100, mode=selector.NumberSelectorMode.SLIDER
            )
        ),
    },
)

SERVICE_SET_PLANT_WATERED_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional(SERVICE_PARAM_DATETIME): cv.string,
    },
)


def get_plant_summary(
    hass: HomeAssistant,
    _service_call: ServiceCall,
) -> ServiceResponse:
    """Return plant summary details and category lists."""
    plants: list[dict[str, object]] = []
    too_dry: list[str] = []
    too_wet: list[str] = []
    unavailable: list[str] = []

    device_registry = dr.async_get(hass)

    for config_entry in hass.config_entries.async_entries(DOMAIN):
        runtime_data = getattr(config_entry, "runtime_data", None)
        if runtime_data is None:
            continue
        runtime = cast("PlantMonitorPlusRuntime", runtime_data)

        # Get the device_id from the device registry
        device_id: str | None = None
        for device in device_registry.devices.values():
            if config_entry.entry_id in device.config_entries:
                device_id = device.id
                break

        evaluation = runtime.evaluate_moisture(hass)
        if not evaluation.available:
            unavailable.append(runtime.name)
        elif evaluation.reason == REASON_TOO_DRY:
            too_dry.append(runtime.name)
        elif evaluation.reason == REASON_TOO_WET:
            too_wet.append(runtime.name)

        moisture_problem_last_modified = runtime.moisture_problem_last_modified
        last_watered = runtime.last_watered
        plants.append(
            {
                ATTR_NAME: runtime.name,
                ATTR_CONFIG_ENTRY_ID: config_entry.entry_id,
                SERVICE_ATTR_DEVICE_ID: device_id,
                SERVICE_ATTR_MOISTURE_CURRENT: evaluation.value,
                SERVICE_ATTR_MOISTURE_MINIMUM: evaluation.minimum_value,
                SERVICE_ATTR_MOISTURE_MAXIMUM: evaluation.maximum_value,
                SERVICE_ATTR_MOISTURE_PROBLEM: evaluation.problem,
                SERVICE_ATTR_MOISTURE_REASON: evaluation.reason,
                SERVICE_ATTR_MOISTURE_PROBLEM_LAST_MODIFIED: (
                    moisture_problem_last_modified.isoformat()
                    if moisture_problem_last_modified
                    else None
                ),
                SERVICE_ATTR_LAST_WATERED: (
                    last_watered.isoformat() if last_watered else None
                ),
                SERVICE_ATTR_LAST_WATERED_DAYS: runtime.last_watered_days,
            }
        )

    return cast(
        "ServiceResponse",
        {
            REASON_TOO_DRY: too_dry,
            REASON_TOO_WET: too_wet,
            SERVICE_ATTR_UNAVAILABLE: unavailable,
            SERVICE_ATTR_PLANTS: plants,
        },
    )


async def async_set_plant_thresholds(
    hass: HomeAssistant,
    service_call: ServiceCall,
) -> None:
    """Set thresholds for a plant."""
    entry: PlantMonitorPlusConfigEntry = service.async_get_config_entry(
        service_call.hass, DOMAIN, service_call.data[ATTR_CONFIG_ENTRY_ID]
    )

    new_options = entry.options.copy()

    if (
        moisture_min := service_call.data.get(SERVICE_PARAM_MOISTURE_MINIMUM)
    ) is not None:
        new_options[CONF_MOISTURE_MINIMUM] = moisture_min

    if (
        moisture_max := service_call.data.get(SERVICE_PARAM_MOISTURE_MAXIMUM)
    ) is not None:
        new_options[CONF_MOISTURE_MAXIMUM] = moisture_max

    if new_options != entry.options:
        hass.config_entries.async_update_entry(entry, options=new_options)


async def async_set_plant_watered(
    hass: HomeAssistant,  # noqa: ARG001
    service_call: ServiceCall,
) -> None:
    """Set the last watered timestamp for a plant."""
    entry: PlantMonitorPlusConfigEntry = service.async_get_config_entry(
        service_call.hass, DOMAIN, service_call.data[ATTR_CONFIG_ENTRY_ID]
    )
    datetime_str: str | None = service_call.data.get(SERVICE_PARAM_DATETIME)

    # Parse datetime or use current UTC time
    if datetime_str:
        try:
            # Parse as local time and convert to UTC
            local_dt = dt_util.parse_datetime(datetime_str)
            if local_dt is None:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="invalid_datetime",
                )

            # Convert local time to UTC
            utc_dt = dt_util.as_utc(local_dt)
        except ValueError as e:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="invalid_datetime"
            ) from e
    else:
        # Use current UTC time
        utc_dt = dt_util.utcnow()

    # Update the timestamp and notify listeners
    await entry.runtime_data.async_set_last_watered(utc_dt)


@callback
async def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services."""
    if hass.services.has_service(DOMAIN, SERVICE_GET_PLANT_SUMMARY):
        return

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PLANT_SUMMARY,
        partial(get_plant_summary, hass),
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PLANT_THRESHOLDS,
        partial(async_set_plant_thresholds, hass),
        schema=SERVICE_SET_PLANT_THRESHOLDS_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PLANT_WATERED,
        partial(async_set_plant_watered, hass),
        schema=SERVICE_SET_PLANT_WATERED_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unregister integration services."""
    hass.services.async_remove(DOMAIN, SERVICE_GET_PLANT_SUMMARY)
    hass.services.async_remove(DOMAIN, SERVICE_SET_PLANT_THRESHOLDS)
    hass.services.async_remove(DOMAIN, SERVICE_SET_PLANT_WATERED)
