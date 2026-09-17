"""Shared entity base class for the Siemens OZW672 integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL, Datapoint
from .coordinator import SiemensOZW672Coordinator


class SiemensOZW672Entity(CoordinatorEntity[SiemensOZW672Coordinator]):
    """Common behaviour for all OZW672 entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SiemensOZW672Coordinator,
        entry: ConfigEntry,
        datapoint: Datapoint,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self.datapoint = datapoint
        self._attr_unique_id = f"{entry.entry_id}_{datapoint.key}"
        self._attr_name = datapoint.name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
            configuration_url=coordinator.client.base_url,
        )

    @property
    def raw_value(self) -> object:
        """Return the current raw value of the datapoint."""
        return self.coordinator.data.get(self.datapoint.key)
