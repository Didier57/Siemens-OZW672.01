"""The Siemens OZW672 integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import OZW672Client
from .const import (
    ATTR_DATAPOINT_ID,
    ATTR_VALUE,
    ATTR_VALUE_TYPE,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USE_HTTPS,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DOMAIN,
    SERVICE_WRITE_DATAPOINT,
    TYPE_ENUMERATION,
    TYPE_NUMERIC,
)
from .coordinator import SiemensOZW672Coordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.BINARY_SENSOR,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def _get_coordinator(entry: ConfigEntry) -> SiemensOZW672Coordinator | None:
    """Return the coordinator of an entry, if it is loaded."""
    coordinator = getattr(entry, "runtime_data", None)
    return coordinator if isinstance(coordinator, SiemensOZW672Coordinator) else None


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the integration services."""

    async def _async_write_datapoint(call: ServiceCall) -> None:
        """Write an arbitrary datapoint value."""
        entry_id: str | None = call.data.get("entry_id")
        coordinators: list[SiemensOZW672Coordinator] = []

        if entry_id:
            entry = hass.config_entries.async_get_entry(entry_id)
            coordinator = _get_coordinator(entry) if entry else None
            if coordinator is not None:
                coordinators.append(coordinator)
        else:
            for entry in hass.config_entries.async_entries(DOMAIN):
                coordinator = _get_coordinator(entry)
                if coordinator is not None:
                    coordinators.append(coordinator)

        if not coordinators:
            raise ValueError("No loaded Siemens OZW672 config entry found")

        for coordinator in coordinators:
            await coordinator.client.async_write_datapoint(
                int(call.data[ATTR_DATAPOINT_ID]),
                call.data[ATTR_VALUE],
                call.data.get(ATTR_VALUE_TYPE, TYPE_NUMERIC),
            )
            await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_WRITE_DATAPOINT,
        _async_write_datapoint,
        schema=vol.Schema(
            {
                vol.Optional("entry_id"): cv.string,
                vol.Required(ATTR_DATAPOINT_ID): vol.All(
                    vol.Coerce(int), vol.Range(min=1)
                ),
                vol.Required(ATTR_VALUE): vol.Any(str, int, float),
                vol.Optional(ATTR_VALUE_TYPE, default=TYPE_NUMERIC): vol.In(
                    [TYPE_NUMERIC, TYPE_ENUMERATION]
                ),
            }
        ),
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Siemens OZW672 config entry."""
    session = async_get_clientsession(hass)
    client = OZW672Client(
        session,
        entry.data[CONF_HOST],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        port=entry.data.get(CONF_PORT),
        use_https=entry.data.get(CONF_USE_HTTPS, False),
        verify_ssl=entry.data.get(CONF_VERIFY_SSL, False),
    )

    coordinator = SiemensOZW672Coordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Siemens OZW672 config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = _get_coordinator(entry)
        if coordinator is not None:
            await coordinator.client.async_logout()
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
