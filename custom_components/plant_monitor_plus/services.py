"""Service registration for plant_monitor_plus."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, cast

from homeassistant.core import SupportsResponse

from .const import DOMAIN, SERVICE_GET_PLANT_SUMMARY

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse

    from .runtime import PlantMonitorRuntime


async def async_get_plant_summary(
    hass: HomeAssistant,
    _service_call: ServiceCall,
) -> ServiceResponse:
    """Return plant summary details and category lists."""
    plants: list[dict[str, object]] = []
    needs_watering: list[str] = []
    too_wet: list[str] = []
    unavailable: list[str] = []

    for config_entry in hass.config_entries.async_entries(DOMAIN):
        runtime_data = getattr(config_entry, "runtime_data", None)
        if runtime_data is None:
            continue
        runtime = cast("PlantMonitorRuntime", runtime_data)

        evaluation = runtime.evaluate_moisture(hass)
        if not evaluation.available:
            unavailable.append(runtime.name)
        elif evaluation.value is not None:
            if evaluation.value < evaluation.min_value:
                needs_watering.append(runtime.name)
            elif evaluation.value > evaluation.max_value:
                too_wet.append(runtime.name)

        last_watered = runtime.last_watered
        plants.append(
            {
                "name": runtime.name,
                "config_entry_id": config_entry.entry_id,
                "current": evaluation.value,
                "min": evaluation.min_value,
                "max": evaluation.max_value,
                "reason": evaluation.reason,
                "last_watered": (last_watered.isoformat() if last_watered else None),
            }
        )

    return {
        "needs_watering": needs_watering,
        "too_wet": too_wet,
        "unavailable": unavailable,
        "plants": plants,
    }


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services."""
    if hass.services.has_service(DOMAIN, SERVICE_GET_PLANT_SUMMARY):
        return

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PLANT_SUMMARY,
        partial(async_get_plant_summary, hass),
        supports_response=SupportsResponse.ONLY,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unregister integration services."""
    hass.services.async_remove(DOMAIN, SERVICE_GET_PLANT_SUMMARY)
