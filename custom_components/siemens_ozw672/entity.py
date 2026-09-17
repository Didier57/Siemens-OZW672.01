"""Shared entity base class for the Siemens OZW672 integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DEVICE_NAME,
    CONF_GATEWAY_FIRMWARE,
    CONF_GATEWAY_SERIAL,
    DOMAIN,
    MANUFACTURER,
    MODEL,
    Datapoint,
)
from .coordinator import SiemensOZW672Coordinator


def build_device_info(
    coordinator: SiemensOZW672Coordinator, entry: ConfigEntry
) -> DeviceInfo:
    """Build the DeviceInfo shared by every entity of an entry."""
    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get(CONF_DEVICE_NAME) or entry.title,
        manufacturer=MANUFACTURER,
        model=entry.data.get(CONF_DEVICE_NAME) or MODEL,
        configuration_url=coordinator.client.base_url,
    )
    serial = entry.data.get(CONF_GATEWAY_SERIAL)
    if serial:
        device_info["serial_number"] = str(serial)
    firmware = entry.data.get(CONF_GATEWAY_FIRMWARE)
    if firmware:
        device_info["sw_version"] = str(firmware)
    return device_info


def _display_name(coordinator: SiemensOZW672Coordinator, datapoint: Datapoint) -> str:
    """Return the entity name, disambiguated by its parent topic if needed.

    Two datapoints of the same controller can share the same title (there are
    for example two ``Message d'erreur`` datapoints), so the parent topic is
    prepended when the title is not unique.
    """
    if not datapoint.path:
        return datapoint.name
    duplicates = any(
        other.path != datapoint.path and other.name == datapoint.name
        for other in coordinator.datapoints
    )
    if not duplicates:
        return datapoint.name
    parts = datapoint.path.split("/")
    if len(parts) >= 2:
        return f"{parts[-2]} {datapoint.name}"
    return datapoint.name


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
        self._attr_name = _display_name(coordinator, datapoint)
        self._attr_device_info = build_device_info(coordinator, entry)

    @property
    def raw_value(self) -> object:
        """Return the current raw value of the datapoint."""
        return self.coordinator.data.get(self.datapoint.key)
