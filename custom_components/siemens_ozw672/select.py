"""Select platform for the Siemens OZW672 integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import PLATFORM_SELECT, Datapoint
from .coordinator import SiemensOZW672Coordinator
from .entity import SiemensOZW672Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select entities."""
    coordinator: SiemensOZW672Coordinator = entry.runtime_data
    async_add_entities(
        SiemensOZW672Select(coordinator, entry, datapoint)
        for datapoint in coordinator.datapoints
        if datapoint.platform == PLATFORM_SELECT and datapoint.options
    )


class SiemensOZW672Select(SiemensOZW672Entity, SelectEntity):
    """A writable enumeration datapoint exposed as a select entity."""

    def __init__(
        self,
        coordinator: SiemensOZW672Coordinator,
        entry: ConfigEntry,
        datapoint: Datapoint,
    ) -> None:
        """Initialise the select entity."""
        super().__init__(coordinator, entry, datapoint)
        self._options = datapoint.options or {}
        self._attr_options = list(self._options.values())

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option.

        The OZW672 reports either the numeric enumeration code or the label
        itself, depending on the firmware, so both shapes are accepted.
        """
        value = self.raw_value
        if value is None:
            return None
        text = str(value).strip()
        if text in self._attr_options:
            return text
        try:
            key = int(text)
        except (TypeError, ValueError):
            return None
        return self._options.get(key)

    async def async_select_option(self, option: str) -> None:
        """Write the selected option to the OZW672.

        The controller refuses a write whose type is not the one it announced
        for the datapoint: a radio button must be written as ``RadioButton``,
        an enumeration as ``Enumeration``. The stored type is therefore used
        rather than always writing an enumeration.
        """
        for key, label in self._options.items():
            if label == option:
                await self.coordinator.client.async_write_datapoint(
                    self.datapoint.id, key, self.datapoint.value_type
                )
                self.coordinator.async_set_updated_data(
                    {**self.coordinator.data, self.datapoint.key: key}
                )
                return
        raise ValueError(f"Unknown option {option!r} for {self.datapoint.name}")
