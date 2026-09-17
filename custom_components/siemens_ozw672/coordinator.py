"""DataUpdateCoordinator for the Siemens OZW672 integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OZW672ApiError, OZW672AuthError, OZW672Client, OZW672ConnectionError
from .const import (
    CONF_CUSTOM_DATAPOINTS,
    CONF_SCAN_INTERVAL,
    DATAPOINTS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORM_SENSOR,
    TYPE_NUMERIC,
    Datapoint,
)

_LOGGER = logging.getLogger(__name__)


def build_datapoints(entry: ConfigEntry) -> list[Datapoint]:
    """Return the datapoints to poll: the built-in catalog plus user defined ones."""
    datapoints: list[Datapoint] = list(DATAPOINTS)
    known_ids = {datapoint.id for datapoint in datapoints}

    custom: dict[str, Any] = entry.options.get(CONF_CUSTOM_DATAPOINTS, {}) or {}
    for raw_id, config in custom.items():
        try:
            datapoint_id = int(raw_id)
        except (TypeError, ValueError):
            _LOGGER.warning("Ignoring custom datapoint with invalid id %r", raw_id)
            continue
        if datapoint_id in known_ids:
            continue

        options = config.get("options") or None
        parsed_options: dict[int, str] | None = None
        if options:
            parsed_options = {}
            for value, label in options.items():
                try:
                    parsed_options[int(value)] = str(label)
                except (TypeError, ValueError):
                    continue

        datapoints.append(
            Datapoint(
                id=datapoint_id,
                key=f"custom_{datapoint_id}",
                name=config.get("name") or f"Datapoint {datapoint_id}",
                platform=config.get("platform") or PLATFORM_SENSOR,
                value_type=config.get("value_type") or TYPE_NUMERIC,
                unit=config.get("unit") or None,
                device_class=config.get("device_class") or None,
                state_class=config.get("state_class") or None,
                options=parsed_options,
                min_value=config.get("min_value"),
                max_value=config.get("max_value"),
                step=config.get("step"),
                custom=True,
            )
        )

    return datapoints


class SiemensOZW672Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the OZW672 and expose the raw datapoint values."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: OZW672Client,
    ) -> None:
        """Initialise the coordinator."""
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.datapoints = build_datapoints(entry)
        self.data: dict[str, Any] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch every known datapoint."""
        try:
            await self.client.async_ensure_session()
        except OZW672AuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except OZW672ConnectionError as err:
            raise UpdateFailed(str(err)) from err

        data: dict[str, Any] = {}
        failures = 0

        for datapoint in self.datapoints:
            try:
                data[datapoint.key] = await self.client.async_read_datapoint(
                    datapoint.id
                )
            except OZW672AuthError as err:
                raise ConfigEntryAuthFailed(str(err)) from err
            except (OZW672ApiError, OZW672ConnectionError) as err:
                failures += 1
                data[datapoint.key] = None
                _LOGGER.debug(
                    "Could not read datapoint %s (%s): %s",
                    datapoint.id,
                    datapoint.name,
                    err,
                )

        if failures == len(self.datapoints) and self.datapoints:
            raise UpdateFailed("None of the OZW672 datapoints could be read")

        return data
