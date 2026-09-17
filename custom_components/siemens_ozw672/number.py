"""Number platform for the Siemens OZW672 integration."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import PLATFORM_NUMBER, TYPE_NUMERIC, Datapoint
from .coordinator import SiemensOZW672Coordinator
from .entity import SiemensOZW672Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number entities."""
    coordinator: SiemensOZW672Coordinator = entry.runtime_data
    async_add_entities(
        SiemensOZW672Number(coordinator, entry, datapoint)
        for datapoint in coordinator.datapoints
        if datapoint.platform == PLATFORM_NUMBER
    )


class SiemensOZW672Number(SiemensOZW672Entity, NumberEntity):
    """A writable numeric datapoint exposed as a number entity."""

    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: SiemensOZW672Coordinator,
        entry: ConfigEntry,
        datapoint: Datapoint,
    ) -> None:
        """Initialise the number entity."""
        super().__init__(coordinator, entry, datapoint)
        self._attr_native_min_value = (
            datapoint.min_value if datapoint.min_value is not None else 0.0
        )
        self._attr_native_max_value = (
            datapoint.max_value if datapoint.max_value is not None else 100.0
        )
        self._attr_native_step = datapoint.step if datapoint.step else 0.5
        if datapoint.unit:
            self._attr_native_unit_of_measurement = datapoint.unit
        if datapoint.device_class:
            try:
                self._attr_device_class = NumberDeviceClass(datapoint.device_class)
            except ValueError:
                self._attr_device_class = None

    @property
    def native_value(self) -> float | None:
        """Return the current setpoint."""
        value = self.raw_value
        if value is None:
            return None
        try:
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Write the new setpoint to the OZW672."""
        await self.coordinator.client.async_write_datapoint(
            self.datapoint.id, value, TYPE_NUMERIC
        )
        self.coordinator.async_set_updated_data(
            {**self.coordinator.data, self.datapoint.key: value}
        )
