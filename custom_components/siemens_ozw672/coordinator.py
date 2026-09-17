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
    CONF_DISABLED_DATAPOINTS,
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
    disabled_ids: set[int] = set()
    for raw_id in entry.options.get(CONF_DISABLED_DATAPOINTS, []) or []:
        try:
            disabled_ids.add(int(raw_id))
        except (TypeError, ValueError):
            _LOGGER.warning("Ignoring disabled datapoint with invalid id %r", raw_id)

    datapoints: list[Datapoint] = [
        datapoint for datapoint in DATAPOINTS if datapoint.id not in disabled_ids
    ]
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
        self._logged_failures: set[str] = set()

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
                if datapoint.key not in self._logged_failures:
                    self._logged_failures.add(datapoint.key)
                    _LOGGER.warning(
                        "Datapoint %s (%s) could not be read: %s",
                        datapoint.id,
                        datapoint.name,
                        err,
                    )
                else:
                    _LOGGER.debug(
                        "Datapoint %s (%s) still not readable: %s",
                        datapoint.id,
                        datapoint.name,
                        err,
                    )

        if failures and failures == len(self.datapoints):
            _LOGGER.error(
                "None of the %s configured OZW672 datapoints could be read. "
                "Datapoint identifiers are generated for the plant, so the "
                "built-in catalog only matches installations built around the "
                "same controller: declare the identifiers of your own plant in "
                "the integration options and disable the ones that do not "
                "apply there.",
                failures,
            )

        return data
