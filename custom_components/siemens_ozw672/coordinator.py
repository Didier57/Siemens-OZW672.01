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
    DEVICE_FIELDS,
    DOMAIN,
    DP_ADDRESS,
    DP_DEVICE,
    DP_DEVICE_CLASS,
    DP_ID,
    DP_MAX_VALUE,
    DP_MIN_VALUE,
    DP_NAME,
    DP_OPTIONS,
    DP_PATH,
    DP_PLATFORM,
    DP_SEGMENTS,
    DP_STATE_CLASS,
    DP_STEP,
    DP_SUBKEY,
    DP_UNIT,
    DP_VALUE_TYPE,
    DP_WRITE_ACCESS,
    PLATFORM_NUMBER,
    PLATFORM_SELECT,
    PLATFORM_SENSOR,
    TYPE_ENUMERATION,
    TYPE_NUMERIC,
    Datapoint,
    guess_device_class,
    guess_state_class,
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


def _config_segments(config: dict[str, Any]) -> list[str] | None:
    """Return the stored path segments of a datapoint configuration.

    Configurations written by version 1.2.1 and older only have the ``path``
    string, which cannot be split reliably because a title may contain a slash.
    Such a path is only split when it contains no ambiguous segment, i.e. when
    no title of the plant contains a slash; otherwise the datapoint simply
    keeps using its saved identifier.
    """
    segments = config.get(DP_SEGMENTS)
    if isinstance(segments, (list, tuple)) and segments:
        return [str(segment) for segment in segments]
    path = config.get(DP_PATH)
    if not path:
        return None
    return [part for part in str(path).split("/") if part]


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


def _generated_keys(entry: ConfigEntry) -> set[str]:
    """Return the keys of the datapoints created by the integration itself.

    Entities added with the generic ``write_datapoint`` service are generated
    datapoints: they are not part of the plant, so they are left untouched.

    """
    generated: set[str] = set()
    for key, config in (entry.options.get(CONF_DATAPOINTS) or {}).items():
        if isinstance(config, dict) and str(key).startswith("generated:"):
            generated.add(str(key))
    return generated


def _apply_config(
    datapoint: Datapoint, configs: dict[str, dict[str, Any]]
) -> Datapoint:
    """Return a datapoint enriched with its freshly stored configuration."""
    config = configs.get(datapoint.key)
    if config is None:
        return datapoint
    return replace(
        datapoint,
        name=config.get(DP_NAME) or datapoint.name,
        platform=config.get(DP_PLATFORM) or datapoint.platform,
        value_type=config.get(DP_VALUE_TYPE) or datapoint.value_type,
        unit=config.get(DP_UNIT) or None,
        device_class=config.get(DP_DEVICE_CLASS) or None,
        state_class=config.get(DP_STATE_CLASS) or None,
        options=_parse_options(config.get(DP_OPTIONS)),
        min_value=_to_float(config.get(DP_MIN_VALUE)),
        max_value=_to_float(config.get(DP_MAX_VALUE)),
        step=_to_float(config.get(DP_STEP)),
    )


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
        segments = _config_segments(config)
        stored_id = config.get(DP_ID)
        try:
            datapoint_id = int(stored_id)
        except (TypeError, ValueError):
            if path is None:
                _LOGGER.warning("Ignoring datapoint %r without a usable id", key)
                continue
            datapoint_id = 0

        current_id = resolved.get(tuple(segments)) if segments else None
        if current_id is not None:
            datapoint_id = int(current_id)

        datapoints.append(
            Datapoint(
                id=datapoint_id,
                name=config.get(DP_NAME) or path or f"Datapoint {datapoint_id}",
                path=path,
                segments=segments,
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

    resolved_ids = set(resolved.values())
    datapoints.extend(_generated_datapoints(entry, exclude_ids=resolved_ids))

    return datapoints


def _generated_datapoints(
    entry: ConfigEntry, exclude_ids: set[int] | None = None
) -> list[Datapoint]:
    """Build the datapoints of entities generated by the user at runtime.

    ``entity.write_datapoint`` stores the datapoints it derives from the
    entities of the entry under a ``generated:`` key, which keeps them out of
    the config entry options edited from the interface.
    """
    exclude_ids = exclude_ids or set()
    generated: list[Datapoint] = []
    for key, config in (entry.options.get(CONF_DATAPOINTS) or {}).items():
        key = str(key)
        if not key.startswith("generated:") or not isinstance(config, dict):
            continue
        datapoint_id = _to_float(config.get(DP_ID))
        if datapoint_id is None:
            continue
        datapoint_id = int(datapoint_id)
        if datapoint_id in exclude_ids:
            continue
        generated.append(
            Datapoint(
                id=datapoint_id,
                name=config.get(DP_NAME) or f"Datapoint {datapoint_id}",
                path=config.get(DP_PATH) or None,
                segments=_config_segments(config),
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
    return generated


def describe_datapoint(write_access: bool, details: dict[str, Any]) -> dict[str, Any]:
    """Return the datapoint fields implied by a device description.

    Shared by the config flow, which builds a datapoint from a description it
    just read, and by the coordinator, which re-checks the description of the
    configured datapoints on every setup.
    """
    value_type = str(details.get("type") or TYPE_NUMERIC)
    unit = details.get("unit") or None
    options = {str(key): label for key, label in (details.get("options") or {}).items()}

    if write_access and options:
        platform = PLATFORM_SELECT
        value_type = TYPE_ENUMERATION
    elif write_access and value_type == TYPE_NUMERIC:
        platform = PLATFORM_NUMBER
    else:
        platform = PLATFORM_SENSOR

    if platform == PLATFORM_NUMBER:
        state_class = None
        minimum = details.get("min")
        maximum = details.get("max")
        resolution = details.get("resolution")
        min_value: float | None = 0.0 if minimum is None else float(minimum)
        max_value: float | None = 100.0 if maximum is None else float(maximum)
        step: float | None = 0.5 if not resolution else float(resolution)
    elif platform == PLATFORM_SELECT:
        state_class = None
        min_value = max_value = step = None
    else:
        state_class = guess_state_class(unit) if value_type == TYPE_NUMERIC else None
        min_value = max_value = step = None

    return {
        DP_NAME: details.get("name") or None,
        DP_PLATFORM: platform,
        DP_VALUE_TYPE: value_type,
        DP_UNIT: unit,
        DP_DEVICE_CLASS: guess_device_class(unit),
        DP_STATE_CLASS: state_class,
        DP_OPTIONS: options or None,
        DP_MIN_VALUE: min_value,
        DP_MAX_VALUE: max_value,
        DP_STEP: step,
    }


def _merge_device_fields(
    config: dict[str, Any],
    fresh: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Adopt the fields the device announces unless the user changed them.

    ``config[DP_DEVICE]`` remembers what the device announced last time, so a
    field of the configuration that differs from that snapshot was edited by
    the user and is kept. A value the device stops reporting (an enumeration
    option list or a range that disappears from the description) is kept too,
    because replacing it with ``None`` would make the entity unusable.
    """
    previous = config.get(DP_DEVICE)
    previous = previous if isinstance(previous, dict) else {}

    merged = dict(config)
    changed: list[str] = []

    for field in DEVICE_FIELDS:
        value = fresh.get(field)
        if field != DP_NAME and value is None:
            continue
        if config.get(field) != previous.get(field):
            continue
        if config.get(field) != value:
            changed.append(field)
        merged[field] = value

    merged[DP_DEVICE] = fresh
    return merged, changed


async def async_resolve_ids(
    client: OZW672Client,
    device_id: int,
    paths: list[list[str]],
) -> dict[tuple[str, ...], int]:
    """Resolve the current identifiers of the given menu tree paths.

    A path is a list of segments, never a ``/`` separated string: the
    controller allows a title to contain a slash, so joining and splitting the
    segments would not round trip and a datapoint could not be found again.
    """
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

    wanted = {tuple(path) for path in paths}
    resolved: dict[tuple[str, ...], int] = {}
    for item in found:
        segments = tuple(item.get(DP_SEGMENTS) or ())
        if segments in wanted and item.get(DP_ID) is not None:
            resolved[segments] = int(item[DP_ID])
    return resolved


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
        self.entry = entry
        self.device_id: int | None = entry.data.get(CONF_DEVICE_ID)
        self.datapoints = build_datapoints(entry)
        self.data: dict[str, Any] = {}
        self._logged_failures: set[str] = set()

    async def async_resolve_identifiers(self) -> None:
        """Check the saved datapoints against the device and refresh them.

        The OZW672 generates the identifiers for the plant it is wired to, so
        they change when the plant or the server parameters are refreshed, and
        a datapoint that was not wired can start reporting values later. Every
        setup (and therefore every reload) therefore walks the menu tree again,
        looks each configured datapoint up by its topic path, and reads the
        description of the datapoint to adapt the entity to what the device
        currently announces (writable or not, unit, range, enumeration values).

        A field that the user edited is never overwritten.
        """
        paths = [
            datapoint.segments for datapoint in self.datapoints if datapoint.segments
        ]
        if paths and self.device_id is not None:
            resolved = await async_resolve_ids(self.client, int(self.device_id), paths)
            moved: dict[int, int] = {}
            for datapoint in self.datapoints:
                current_id = (
                    resolved.get(tuple(datapoint.segments))
                    if datapoint.segments
                    else None
                )
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
                    continue
                if current_id != datapoint.id:
                    _LOGGER.info(
                        "Datapoint '%s' changed identifier from %s to %s",
                        datapoint.path,
                        datapoint.id,
                        current_id,
                    )
                    moved[datapoint.id] = int(current_id)

            if moved:
                self.datapoints = [
                    replace(datapoint, id=moved[datapoint.id])
                    if datapoint.id in moved
                    else datapoint
                    for datapoint in self.datapoints
                ]

        await self._async_refresh_descriptions()

    async def _async_refresh_descriptions(self) -> None:
        """Adapt every configured datapoint to its current device description."""
        if not self.datapoints:
            return

        stored: dict[str, dict[str, Any]] = {}
        for key, config in (self.entry.options.get(CONF_DATAPOINTS) or {}).items():
            if isinstance(config, dict):
                stored[str(key)] = dict(config)

        skip = _generated_keys(self.entry)
        updated: dict[str, dict[str, Any]] = {}
        changes: list[str] = []

        for datapoint in self.datapoints:
            config = stored.get(datapoint.key)
            if config is None or datapoint.key in skip:
                continue
            try:
                details = await self.client.async_read_datapoint_description(
                    datapoint.id
                )
            except OZW672Error as err:
                _LOGGER.debug(
                    "No description for datapoint %s (%s): %s",
                    datapoint.id,
                    datapoint.key,
                    err,
                )
                continue

            fresh = describe_datapoint(datapoint.write_access, details)
            merged, changed = _merge_device_fields(config, fresh)
            updated[datapoint.key] = merged
            if changed:
                changes.append(f"{datapoint.key} ({', '.join(sorted(changed))})")

        if not updated:
            return

        if changes:
            _LOGGER.info(
                "The OZW672 description changed for %s datapoint(s): %s",
                len(changes),
                "; ".join(changes),
            )

        self.datapoints = [
            _apply_config(datapoint, updated) for datapoint in self.datapoints
        ]

        options = dict(self.entry.options)
        datapoints = dict(options.get(CONF_DATAPOINTS) or {})
        datapoints.update(updated)
        options[CONF_DATAPOINTS] = datapoints
        self.hass.config_entries.async_update_entry(self.entry, options=options)

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
