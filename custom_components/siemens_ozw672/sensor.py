"""Sensor platform for the Siemens OZW672 integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import PLATFORM_SENSOR, Datapoint
from .coordinator import SiemensOZW672Coordinator
from .entity import SiemensOZW672Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor entities."""
    coordinator: SiemensOZW672Coordinator = entry.runtime_data
    async_add_entities(
        SiemensOZW672Sensor(coordinator, entry, datapoint)
        for datapoint in coordinator.datapoints
        if datapoint.platform == PLATFORM_SENSOR
    )


def _device_class(value: str | None) -> SensorDeviceClass | None:
    """Convert a string into a SensorDeviceClass when possible."""
    if not value:
        return None
    try:
        return SensorDeviceClass(value)
    except ValueError:
        return None


def _state_class(value: str | None) -> SensorStateClass | None:
    """Convert a string into a SensorStateClass when possible."""
    if not value:
        return None
    try:
        return SensorStateClass(value)
    except ValueError:
        return None


class SiemensOZW672Sensor(SiemensOZW672Entity, SensorEntity):
    """A read-only datapoint exposed as a sensor."""

    def __init__(
        self,
        coordinator: SiemensOZW672Coordinator,
        entry: ConfigEntry,
        datapoint: Datapoint,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, entry, datapoint)
        if datapoint.unit:
            self._attr_native_unit_of_measurement = datapoint.unit
        self._attr_device_class = _device_class(datapoint.device_class)
        self._attr_state_class = _state_class(datapoint.state_class)

    @property
    def native_value(self) -> Any:
        """Return the current value of the datapoint."""
        value = self.raw_value
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return value
        text = str(value).strip()
        if not text:
            return None
        try:
            return float(text.replace(",", "."))
        except ValueError:
            if self._attr_state_class is not None:
                return None
            return text
