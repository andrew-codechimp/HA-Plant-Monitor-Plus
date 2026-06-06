"""Repairs for plant_monitor_plus."""

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.core import HomeAssistant

from .const import ISSUE_MOISTURE_ENTITY_INVALID


async def async_create_fix_flow(
    _hass: HomeAssistant,
    issue_id: str,
    _data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create a message-only flow for moisture source entity issues."""
    if not issue_id.startswith(f"{ISSUE_MOISTURE_ENTITY_INVALID}_"):
        return ConfirmRepairFlow()

    return ConfirmRepairFlow()
