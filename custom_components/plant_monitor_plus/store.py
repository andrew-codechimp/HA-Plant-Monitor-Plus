"""Persistent storage for plant_monitor_plus device data."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.core import HomeAssistant

STORE_VERSION = 1
STORE_KEY = DOMAIN
STORE_DEVICES_KEY = "devices"
STORE_LAST_WATERED_KEY = "last_watered"


class PlantMonitorStore:
    """Persist per-entry data for all plant monitor devices."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the shared integration store."""
        self._store = Store(hass, STORE_VERSION, STORE_KEY)
        self._devices: dict[str, dict[str, Any]] = {}

    def device_data(self, entry_id: str) -> dict[str, Any]:
        """Return cached data for one device entry."""
        return dict(self._devices.get(entry_id, {}))

    async def async_load(self) -> None:
        """Load persisted device data for all entries."""
        data = await self._store.async_load() or {}
        devices = data.get(STORE_DEVICES_KEY, {})
        if isinstance(devices, dict):
            self._devices = {
                str(entry_id): dict(device_data)
                for entry_id, device_data in devices.items()
                if isinstance(device_data, dict)
            }
        else:
            self._devices = {}

    def last_watered(self, entry_id: str) -> datetime | None:
        """Return the cached last watering timestamp for a device."""
        device_data = self._devices.get(entry_id, {})
        last_watered = device_data.get(STORE_LAST_WATERED_KEY)
        if last_watered is None:
            return None

        return dt_util.parse_datetime(str(last_watered))

    def async_update_device_data(self, entry_id: str, **values: Any) -> None:
        """Persist one or more values for a device entry."""
        device_data = self._devices.setdefault(entry_id, {})
        device_data.update(values)
        self._store.async_delay_save(self._async_store_data, 0)

    def async_update_last_watered(
        self,
        entry_id: str,
        last_watered: datetime | None,
    ) -> None:
        """Persist a new watering timestamp for a device."""
        self.async_update_device_data(
            entry_id,
            **{
                STORE_LAST_WATERED_KEY: (
                    last_watered.isoformat() if last_watered is not None else None
                )
            },
        )

    def _async_store_data(self) -> dict[str, str | None]:
        """Serialize the stored payload."""
        return {
            STORE_DEVICES_KEY: self._devices,
        }
