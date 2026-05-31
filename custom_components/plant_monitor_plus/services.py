"""Service registration for plant_monitor_plus."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, cast

import voluptuous as vol

from homeassistant.const import ATTR_NAME
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_LAST_WATERED,
    DOMAIN,
    REASON_TOO_DRY,
    REASON_TOO_WET,
    SERVICE_ATTR_MOISTURE_CURRENT,
    SERVICE_ATTR_MOISTURE_LAST_MODIFIED,
    SERVICE_ATTR_MOISTURE_MAXIMUM,
    SERVICE_ATTR_MOISTURE_MINIMUM,
    SERVICE_ATTR_MOISTURE_PROBLEM,
    SERVICE_ATTR_MOISTURE_REASON,
    SERVICE_GET_PLANT_SUMMARY,
    SERVICE_SET_PLANT_WATERED,
)

if TYPE_CHECKING:
    from custom_components.plant_monitor_plus.runtime import PlantMonitorPlusRuntime

SERVICE_SET_PLANT_WATERED_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Optional("datetime"): cv.string,
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

    for config_entry in hass.config_entries.async_entries(DOMAIN):
        runtime_data = getattr(config_entry, "runtime_data", None)
        if runtime_data is None:
            continue
        runtime = cast("PlantMonitorPlusRuntime", runtime_data)

        evaluation = runtime.evaluate_moisture(hass)
        if not evaluation.available:
            unavailable.append(runtime.name)
        elif evaluation.reason == REASON_TOO_DRY:
            too_dry.append(runtime.name)
        elif evaluation.reason == REASON_TOO_WET:
            too_wet.append(runtime.name)

        moisture_last_modified = runtime.moisture_last_modified
        last_watered = runtime.last_watered
        plants.append(
            {
                ATTR_NAME: runtime.name,
                "config_entry_id": config_entry.entry_id,
                SERVICE_ATTR_MOISTURE_CURRENT: evaluation.value,
                SERVICE_ATTR_MOISTURE_MINIMUM: evaluation.minimum_value,
                SERVICE_ATTR_MOISTURE_MAXIMUM: evaluation.maximum_value,
                SERVICE_ATTR_MOISTURE_PROBLEM: evaluation.problem,
                SERVICE_ATTR_MOISTURE_REASON: evaluation.reason,
                SERVICE_ATTR_MOISTURE_LAST_MODIFIED: (
                    moisture_last_modified.isoformat()
                    if moisture_last_modified
                    else None
                ),
                ATTR_LAST_WATERED: (last_watered.isoformat() if last_watered else None),
            }
        )

    return cast(
        "ServiceResponse",
        {
            REASON_TOO_DRY: too_dry,
            REASON_TOO_WET: too_wet,
            "unavailable": unavailable,
            "plants": plants,
        },
    )


async def async_set_plant_watered(
    hass: HomeAssistant,
    service_call: ServiceCall,
) -> None:
    """Set the last watered timestamp for a plant."""
    config_entry_id: str = service_call.data.get("config_entry_id", "")
    datetime_str: str | None = service_call.data.get("datetime")

    # Validate config_entry_id exists in this domain and get runtime
    runtime = None
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id == config_entry_id:
            runtime_data = getattr(entry, "runtime_data", None)
            if runtime_data is not None:
                runtime = cast("PlantMonitorPlusRuntime", runtime_data)
            break

    if runtime is None:
        msg = f"Config entry '{config_entry_id}' not found in {DOMAIN} domain"
        raise ServiceValidationError(msg)

    # Parse datetime or use current UTC time
    if datetime_str:
        try:
            # Parse as local time and convert to UTC
            local_dt = dt_util.parse_datetime(datetime_str)
            if local_dt is None:
                msg = f"Invalid datetime format: '{datetime_str}'"
                raise ServiceValidationError(msg)
            # Convert local time to UTC
            utc_dt = dt_util.as_utc(local_dt)
        except ValueError as e:
            msg = f"Invalid datetime: {e}"
            raise ServiceValidationError(msg) from e
    else:
        # Use current UTC time
        utc_dt = dt_util.utcnow()

    # Update the timestamp and notify listeners
    await runtime.async_set_last_watered(utc_dt)


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
        SERVICE_SET_PLANT_WATERED,
        partial(async_set_plant_watered, hass),
        schema=SERVICE_SET_PLANT_WATERED_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unregister integration services."""
    hass.services.async_remove(DOMAIN, SERVICE_GET_PLANT_SUMMARY)
    hass.services.async_remove(DOMAIN, SERVICE_SET_PLANT_WATERED)
