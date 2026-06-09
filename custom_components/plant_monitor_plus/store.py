"""Persistent storage for plant_monitor_plus device data."""

from collections import OrderedDict
from collections.abc import MutableMapping
from datetime import datetime
from typing import Any, cast

import attr

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION_MAJOR = 1
STORAGE_VERSION_MINOR = 1
DATA_REGISTRY = f"{DOMAIN}_storage"
STORAGE_KEY = f"{DOMAIN}.storage"

SAVE_DELAY = 10


@attr.s(slots=True, frozen=True)
class DeviceEntry:
    # pylint: disable=too-few-public-methods
    """Plant Device storage Entry."""

    device_id = attr.ib(type=str, default=None)
    moisture_problem_state = attr.ib(type=bool, default=None)
    moisture_problem_last_modified = attr.ib(type=datetime, default=None)
    last_watered = attr.ib(type=datetime, default=None)


class MigratableStore(Store):
    """Holds plant data."""

    async def _async_migrate_func(
        self,
        old_major_version: int,  # noqa: ARG002
        old_minor_version: int,  # noqa: ARG002
        data: dict,
    ):
        # Do nothing for now
        return data


class PlantMonitorStorage:
    """Persist per-entry data for all plant monitor devices."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the shared integration store."""
        self.hass = hass
        self.devices: MutableMapping[str, DeviceEntry] = {}
        self._store = MigratableStore(
            hass,
            STORAGE_VERSION_MAJOR,
            STORAGE_KEY,
            minor_version=STORAGE_VERSION_MINOR,
        )

    async def async_load(self) -> None:
        """Load persisted device data for all entries."""
        data = await self._store.async_load()
        devices: OrderedDict[str, DeviceEntry] = OrderedDict()

        if data is not None and "devices" in data:
            for device in data["devices"]:
                devices[device["device_id"]] = DeviceEntry(**device)

        self.devices = devices

    @callback
    def async_schedule_save(self) -> None:
        """Schedule saving the registry."""
        self._store.async_delay_save(self._data_to_save, SAVE_DELAY)

    async def async_save(self) -> None:
        """Save the registry."""
        await self._store.async_save(self._data_to_save())

    @callback
    def _data_to_save(self) -> dict:
        """Return data for the registry to store in a file."""
        store_data = {}
        store_data["devices"] = [attr.asdict(entry) for entry in self.devices.values()]
        return store_data

    @callback
    def async_get_device(self, device_id) -> dict[str, Any] | None:
        """Get an existing DeviceEntry by id."""
        res = self.devices.get(device_id)
        return attr.asdict(res) if res else None

    @callback
    def async_get_devices(self):
        """Get existing devices."""
        res = {}
        for key, val in self.devices.items():
            res[key] = attr.asdict(val)
        return res

    @callback
    def async_create_device(self, device_id: str, data: dict) -> DeviceEntry | None:
        """Create a new DeviceEntry."""
        if device_id in self.devices:
            return None
        new_device = DeviceEntry(**data, device_id=device_id)
        self.devices[device_id] = new_device
        self.async_schedule_save()
        return new_device

    @callback
    def async_delete_device(self, device_id: str) -> bool:
        """Delete DeviceEntry."""
        if device_id in self.devices:
            del self.devices[device_id]
            self.async_schedule_save()
            return True
        return False

    @callback
    def async_update_device(self, device_id: str, changes: dict) -> DeviceEntry:
        """Update existing DeviceEntry."""
        old = self.devices[device_id]
        new = self.devices[device_id] = attr.evolve(old, **changes)
        self.async_schedule_save()
        return new


async def async_get_registry(hass: HomeAssistant) -> PlantMonitorStorage:
    """Return plant monitor storage instance."""
    task = hass.data.get(DATA_REGISTRY)

    if task is None:

        async def _load_reg() -> PlantMonitorStorage:
            registry = PlantMonitorStorage(hass)
            await registry.async_load()
            return registry

        task = hass.data[DATA_REGISTRY] = hass.async_create_task(_load_reg())

    return cast(PlantMonitorStorage, await task)
