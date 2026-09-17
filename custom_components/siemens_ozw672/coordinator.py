"""DataUpdateCoordinator for the Siemens OZW672 integration."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    OZW672ApiError,
    OZW672AuthError,
    OZW672Client,
    OZW672ConnectionError,
    OZW672Error,
)
from .const import (
    CONF_DATAPOINTS,
    CONF_DEVICE_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    DP_ADDRESS,
    DP_DEVICE_CLASS,
    DP_ID,
    DP_MAX_VALUE,
    DP_MIN_VALUE,
    DP_NAME,
    DP_OPTIONS,
    DP_PATH,
    DP_PLATFORM,
    DP_STATE_CLASS,
    DP_STEP,
    DP_SUBKEY,
    DP_UNIT,
    DP_VALUE_TYPE,
    DP_WRITE_ACCESS,
    PLATFORM_SENSOR,
    TYPE_NUMERIC,
    Datapoint,
)

_LOGGER = logging.getLogger(__name__)


def _to_float(value: Any) -> float | None:
    """Convert a stored value into a float when possible."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_options(raw: Any) -> dict[int, str] | None:
    """Convert a ``{"1": "Label"}`` mapping into ``{1: "Label"}``."""
    if not isinstance(raw, dict):
        return None
    options: dict[int, str] = {}
    for value, label in raw.items():
        try:
            options[int(value)] = str(label)
        except (TypeError, ValueError):
            continue
    return options or None


def build_datapoints(
    entry: ConfigEntry, resolved: dict[str, int] | None = None
) -> list[Datapoint]:
    """Build the datapoints declared in the options of an entry.

    ``resolved`` maps a datapoint path to the identifier currently used by the
    OZW672 for that path. The identifier stored in the options is only a cache
    and is used as a fallback when the menu tree could not be read.
    """
    resolved = resolved or {}
    datapoints: list[Datapoint] = []

    for key, config in (entry.options.get(CONF_DATAPOINTS) or {}).items():
        if not isinstance(config, dict):
            continue
        path = config.get(DP_PATH) or None
        stored_id = config.get(DP_ID)
        try:
            datapoint_id = int(stored_id)
        except (TypeError, ValueError):
            if path is None:
                _LOGGER.warning("Ignoring datapoint %r without a usable id", key)
                continue
            datapoint_id = 0

        current_id = resolved.get(path) if path else None
        if current_id is not None:
            datapoint_id = int(current_id)

        datapoints.append(
            Datapoint(
                id=datapoint_id,
                name=config.get(DP_NAME) or path or f"Datapoint {datapoint_id}",
                path=path,
                address=config.get(DP_ADDRESS) or None,
                subkey=config.get(DP_SUBKEY),
                write_access=bool(config.get(DP_WRITE_ACCESS, False)),
                platform=config.get(DP_PLATFORM) or PLATFORM_SENSOR,
                value_type=config.get(DP_VALUE_TYPE) or TYPE_NUMERIC,
                unit=config.get(DP_UNIT) or None,
                device_class=config.get(DP_DEVICE_CLASS) or None,
                state_class=config.get(DP_STATE_CLASS) or None,
                options=_parse_options(config.get(DP_OPTIONS)),
                min_value=_to_float(config.get(DP_MIN_VALUE)),
                max_value=_to_float(config.get(DP_MAX_VALUE)),
                step=_to_float(config.get(DP_STEP)),
            )
        )

    return datapoints


async def async_resolve_ids(
    client: OZW672Client,
    device_id: int,
    paths: list[str],
) -> dict[str, int]:
    """Resolve the current identifiers of the given menu tree paths."""
    if not paths:
        return {}
    try:
        found = await client.async_walk_datapoints(device_id, wanted_paths=paths)
    except OZW672Error as err:
        _LOGGER.warning(
            "Could not read the OZW672 menu tree to check the datapoint "
            "identifiers: %s",
            err,
        )
        return {}

    wanted = set(paths)
    return {
        str(item[DP_PATH]): int(item[DP_ID])
        for item in found
        if item.get(DP_PATH) in wanted and item.get(DP_ID) is not None
    }


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
        self.device_id: int | None = entry.data.get(CONF_DEVICE_ID)
        self.datapoints = build_datapoints(entry)
        self.data: dict[str, Any] = {}
        self._logged_failures: set[str] = set()

    async def async_resolve_identifiers(self) -> None:
        """Check that the saved datapoint identifiers still match the names.

        The OZW672 generates the identifiers for the plant it is wired to, so
        they change when the plant or the server parameters are refreshed.
        Every setup (and therefore every reload) walks the menu tree again and
        looks each configured datapoint up by its topic path.
        """
        paths = [datapoint.path for datapoint in self.datapoints if datapoint.path]
        if not paths or self.device_id is None:
            return

        resolved = await async_resolve_ids(self.client, int(self.device_id), paths)
        if not resolved:
            return

        updated: list[Datapoint] = []
        for datapoint in self.datapoints:
            current_id = resolved.get(datapoint.path) if datapoint.path else None
            if current_id is None:
                if datapoint.path:
                    _LOGGER.warning(
                        "Datapoint '%s' was not found in the OZW672 menu tree "
                        "anymore; keeping the saved identifier %s. If the "
                        "topics of the device changed, remove and add this "
                        "datapoint again.",
                        datapoint.path,
                        datapoint.id,
                    )
                updated.append(datapoint)
                continue
            if current_id != datapoint.id:
                _LOGGER.info(
                    "Datapoint '%s' changed identifier from %s to %s",
                    datapoint.path,
                    datapoint.id,
                    current_id,
                )
                datapoint = replace(datapoint, id=int(current_id))
            updated.append(datapoint)

        self.datapoints = updated

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
                        datapoint.key,
                        err,
                    )
                else:
                    _LOGGER.debug(
                        "Datapoint %s (%s) still not readable: %s",
                        datapoint.id,
                        datapoint.key,
                        err,
                    )

        if failures and failures == len(self.datapoints):
            _LOGGER.error(
                "None of the %s configured OZW672 datapoints could be read. "
                "The identifiers of a plant are generated by the OZW672 itself "
                "and the topics configured for this entry do not seem to exist "
                "anymore: edit the integration options to select the "
                "datapoints of your installation again.",
                failures,
            )

        return data
