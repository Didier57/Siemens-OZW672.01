"""Binary sensor platform for the Siemens OZW672 integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import SiemensOZW672Coordinator
from .entity import build_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the connectivity binary sensor."""
    coordinator: SiemensOZW672Coordinator = entry.runtime_data
    async_add_entities([SiemensOZW672Connectivity(coordinator, entry)])


class SiemensOZW672Connectivity(
    CoordinatorEntity[SiemensOZW672Coordinator], BinarySensorEntity
):
    """Report whether the OZW672 answered the last poll."""

    _attr_has_entity_name = True
    _attr_translation_key = "connectivity"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: SiemensOZW672Coordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialise the connectivity sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_connectivity"
        self._attr_device_info = build_device_info(coordinator, entry)

    @property
    def is_on(self) -> bool:
        """Return True when at least one datapoint was read successfully."""
        return any(value is not None for value in self.coordinator.data.values())
