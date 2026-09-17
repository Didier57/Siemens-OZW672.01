"""Config and options flow for the Siemens OZW672 integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    OZW672ApiError,
    OZW672AuthError,
    OZW672Client,
    OZW672ConnectionError,
    OZW672Error,
)
from .const import (
    CONF_CUSTOM_DATAPOINTS,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_DISABLED_DATAPOINTS,
    CONF_GATEWAY_FIRMWARE,
    CONF_GATEWAY_SERIAL,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USE_HTTPS,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DATAPOINTS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    PLATFORM_NUMBER,
    PLATFORM_SELECT,
    PLATFORM_SENSOR,
    SELECTOR_VALUE_TYPE_ENUMERATION,
    SELECTOR_VALUE_TYPE_NUMERIC,
    TYPE_ENUMERATION,
    TYPE_NUMERIC,
    VALUE_TYPE_SELECTOR_TO_API,
)

_LOGGER = logging.getLogger(__name__)

MENU_ADD_DATAPOINT = "add_datapoint"
MENU_BUILTIN_DATAPOINTS = "builtin_datapoints"
MENU_REMOVE_DATAPOINT = "remove_datapoint"
MENU_SETTINGS = "settings"


def _normalise(user_input: dict[str, Any]) -> dict[str, Any]:
    """Clean up the host field and detect an explicit scheme."""
    data = dict(user_input)
    host = str(data.get(CONF_HOST, "")).strip()
    use_https = bool(data.get(CONF_USE_HTTPS, False))

    lowered = host.lower()
    for prefix, https in (("https://", True), ("http://", False)):
        if lowered.startswith(prefix):
            host = host[len(prefix) :]
            use_https = https
            break

    data[CONF_HOST] = host.strip("/").split("/")[0]
    data[CONF_USE_HTTPS] = use_https
    port = data.get(CONF_PORT)
    if port in (None, ""):
        data.pop(CONF_PORT, None)
    else:
        data[CONF_PORT] = int(float(port))
    return data


def _client(hass: HomeAssistant, data: dict[str, Any]) -> OZW672Client:
    """Build a client from the connection data."""
    return OZW672Client(
        async_get_clientsession(hass),
        data[CONF_HOST],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
        port=data.get(CONF_PORT),
        use_https=data.get(CONF_USE_HTTPS, False),
        verify_ssl=data.get(CONF_VERIFY_SSL, False),
    )


async def _async_validate(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the credentials against the device."""
    client = _client(hass, data)
    try:
        await client.async_login()
    finally:
        await client.async_logout()


async def _async_probe(
    hass: HomeAssistant, data: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Collect the devices of the plant and the gateway information.

    Logging in proves the credentials; listing the devices or reading the
    gateway information may still be unsupported by a given firmware, in which
    case setup continues without them.
    """
    client = _client(hass, data)
    await client.async_login()
    try:
        try:
            devices = await client.async_list_devices()
        except OZW672Error as err:
            _LOGGER.warning("Cannot list the OZW672 devices: %s", err)
            devices = []
        try:
            info = await client.async_get_device_info()
        except OZW672Error as err:
            _LOGGER.warning("Cannot read the OZW672 gateway information: %s", err)
            info = {}
        return devices, info
    finally:
        await client.async_logout()


def _user_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Build the connection schema."""
    defaults = defaults or {}
    port_key: vol.Marker = vol.Optional(CONF_PORT)
    if defaults.get(CONF_PORT):
        port_key = vol.Optional(
            CONF_PORT, description={"suggested_value": defaults[CONF_PORT]}
        )
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            port_key: NumberSelector(
                NumberSelectorConfig(
                    min=1, max=65535, step=1, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Required(
                CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, "")
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            vol.Optional(
                CONF_USE_HTTPS, default=defaults.get(CONF_USE_HTTPS, False)
            ): BooleanSelector(),
            vol.Optional(
                CONF_VERIFY_SSL, default=defaults.get(CONF_VERIFY_SSL, False)
            ): BooleanSelector(),
        }
    )


def _parse_enum_options(raw: str | None) -> dict[int, str] | None:
    """Parse a '1=Automatic, 2=Reduced' style string."""
    if not raw:
        return None
    options: dict[int, str] = {}
    for chunk in str(raw).replace("\n", ",").split(","):
        chunk = chunk.strip()
        if not chunk or "=" not in chunk:
            continue
        key, _, label = chunk.partition("=")
        try:
            options[int(key.strip())] = label.strip()
        except ValueError:
            continue
    return options or None


def _datapoint_schema() -> vol.Schema:
    """Build the schema used to declare a custom datapoint."""
    return vol.Schema(
        {
            vol.Required("datapoint_id"): NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=999999,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required("name"): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Required("platform", default=PLATFORM_SENSOR): SelectSelector(
                SelectSelectorConfig(
                    options=[PLATFORM_SENSOR, PLATFORM_NUMBER, PLATFORM_SELECT],
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="platform",
                )
            ),
            vol.Required(
                "value_type", default=SELECTOR_VALUE_TYPE_NUMERIC
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        SELECTOR_VALUE_TYPE_NUMERIC,
                        SELECTOR_VALUE_TYPE_ENUMERATION,
                    ],
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="value_type",
                )
            ),
            vol.Optional("unit", default=""): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Optional("device_class", default=""): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Optional("state_class", default=""): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Optional("enum_options", default=""): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Optional("min_value"): NumberSelector(
                NumberSelectorConfig(mode=NumberSelectorMode.BOX, step="any")
            ),
            vol.Optional("max_value"): NumberSelector(
                NumberSelectorConfig(mode=NumberSelectorMode.BOX, step="any")
            ),
            vol.Optional("step"): NumberSelector(
                NumberSelectorConfig(mode=NumberSelectorMode.BOX, step="any")
            ),
        }
    )


class SiemensOZW672ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the configuration flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the flow."""
        self._reauth_entry: ConfigEntry | None = None
        self._connection: dict[str, Any] = {}
        self._devices: list[dict[str, Any]] = []
        self._gateway: dict[str, Any] = {}

    def _async_create_entry(
        self, device_id: int | None = None, device_name: str | None = None
    ) -> FlowResult:
        """Create the config entry for the connection and the chosen device."""
        data = dict(self._connection)
        firmware = self._gateway.get("FwVersion")
        serial = self._gateway.get("SerialNr")
        if firmware:
            data[CONF_GATEWAY_FIRMWARE] = str(firmware)
        if serial:
            data[CONF_GATEWAY_SERIAL] = str(serial)
        if device_id is not None:
            data[CONF_DEVICE_ID] = int(device_id)
        if device_name:
            data[CONF_DEVICE_NAME] = device_name
        title = device_name or data[CONF_HOST]
        return self.async_create_entry(title=title, data=data)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = _normalise(user_input)
            try:
                devices, gateway = await _async_probe(self.hass, data)
            except OZW672AuthError as err:
                _LOGGER.warning("OZW672 authentication failed: %s", err)
                errors["base"] = "invalid_auth"
            except OZW672ConnectionError as err:
                _LOGGER.error("Cannot reach the OZW672: %s", err)
                errors["base"] = "cannot_connect"
            except OZW672ApiError as err:
                _LOGGER.error("Unexpected OZW672 response: %s", err)
                errors["base"] = "unknown"
            except Exception:
                _LOGGER.exception("Unexpected error while validating the OZW672")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(data[CONF_HOST].lower())
                self._abort_if_unique_id_configured()
                self._connection = data
                self._devices = devices
                self._gateway = gateway
                if devices:
                    return await self.async_step_device()
                return self._async_create_entry()

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user select the plant device to use.

        A single OZW672 usually serves one controller, but it can also be
        wired to several controllers on the same bus. Datapoint identifiers
        depend on the plant, so the device list is read from the menutree of
        the OZW672 itself.
        """
        if user_input is not None:
            raw_id = user_input[CONF_DEVICE_ID]
            name = None
            for device in self._devices:
                if str(device["id"]) == str(raw_id):
                    name = device["name"]
                    break
            return self._async_create_entry(int(raw_id), name)

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(
                                    value=str(device["id"]), label=device["name"]
                                )
                                for device in self._devices
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Start a re-authentication."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for new credentials."""
        errors: dict[str, str] = {}
        entry = self._reauth_entry
        if entry is None:
            return self.async_abort(reason="reauth_successful")

        if user_input is not None:
            data = {
                **entry.data,
                CONF_USERNAME: user_input[CONF_USERNAME],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            try:
                await _async_validate(self.hass, data)
            except OZW672AuthError as err:
                _LOGGER.warning("OZW672 authentication failed: %s", err)
                errors["base"] = "invalid_auth"
            except OZW672ConnectionError as err:
                _LOGGER.error("Cannot reach the OZW672: %s", err)
                errors["base"] = "cannot_connect"
            except OZW672ApiError as err:
                _LOGGER.error("Unexpected OZW672 response: %s", err)
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(entry, data=data)
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME, default=entry.data.get(CONF_USERNAME, "")
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SiemensOZW672OptionsFlow:
        """Return the options flow handler."""
        return SiemensOZW672OptionsFlow()


class SiemensOZW672OptionsFlow(OptionsFlow):
    """Handle the options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the options menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                MENU_SETTINGS,
                MENU_BUILTIN_DATAPOINTS,
                MENU_ADD_DATAPOINT,
                MENU_REMOVE_DATAPOINT,
            ],
        )

    async def async_step_builtin_datapoints(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Enable or disable the datapoints of the built-in catalog.

        The catalog matches the reference installation only, so datapoints that
        do not exist on another plant have to be disabled before they can be
        replaced by custom ones.
        """
        if user_input is not None:
            options = {
                **self.config_entry.options,
                CONF_DISABLED_DATAPOINTS: list(user_input.get("disabled", [])),
            }
            return self.async_create_entry(data=options)

        choices = [
            SelectOptionDict(
                value=str(datapoint.id),
                label=f"{datapoint.name} (id {datapoint.id})",
            )
            for datapoint in DATAPOINTS
        ]
        current = [
            str(raw_id)
            for raw_id in self.config_entry.options.get(CONF_DISABLED_DATAPOINTS, [])
            or []
        ]
        return self.async_show_form(
            step_id=MENU_BUILTIN_DATAPOINTS,
            data_schema=vol.Schema(
                {
                    vol.Optional("disabled", default=current): SelectSelector(
                        SelectSelectorConfig(
                            options=choices,
                            multiple=True,
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Update the polling interval."""
        if user_input is not None:
            options = {**self.config_entry.options, **user_input}
            return self.async_create_entry(data=options)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        return self.async_show_form(
            step_id=MENU_SETTINGS,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=1,
                            unit_of_measurement="s",
                            mode=NumberSelectorMode.BOX,
                        )
                    )
                }
            ),
        )

    async def async_step_add_datapoint(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Declare an extra datapoint."""
        errors: dict[str, str] = {}
        custom: dict[str, Any] = dict(
            self.config_entry.options.get(CONF_CUSTOM_DATAPOINTS, {}) or {}
        )

        if user_input is not None:
            datapoint_id = str(int(user_input["datapoint_id"]))
            disabled = {
                str(raw_id)
                for raw_id in self.config_entry.options.get(
                    CONF_DISABLED_DATAPOINTS, []
                )
                or []
            }
            known = {str(item.id) for item in DATAPOINTS} - disabled
            if datapoint_id in custom or datapoint_id in known:
                errors["datapoint_id"] = "duplicate"
            else:
                enum_options = _parse_enum_options(user_input.get("enum_options"))
                platform = user_input["platform"]
                if enum_options and platform == PLATFORM_SENSOR:
                    platform = PLATFORM_SELECT
                value_type = VALUE_TYPE_SELECTOR_TO_API.get(
                    str(user_input["value_type"]), TYPE_NUMERIC
                )
                custom[datapoint_id] = {
                    "name": user_input["name"],
                    "platform": platform,
                    "value_type": (TYPE_ENUMERATION if enum_options else value_type),
                    "unit": user_input.get("unit") or None,
                    "device_class": user_input.get("device_class") or None,
                    "state_class": user_input.get("state_class") or None,
                    "options": enum_options,
                    "min_value": user_input.get("min_value"),
                    "max_value": user_input.get("max_value"),
                    "step": user_input.get("step"),
                }
                options = {
                    **self.config_entry.options,
                    CONF_CUSTOM_DATAPOINTS: custom,
                }
                return self.async_create_entry(data=options)

        return self.async_show_form(
            step_id=MENU_ADD_DATAPOINT,
            data_schema=_datapoint_schema(),
            errors=errors,
        )

    async def async_step_remove_datapoint(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove previously declared datapoints."""
        custom: dict[str, Any] = dict(
            self.config_entry.options.get(CONF_CUSTOM_DATAPOINTS, {}) or {}
        )
        if not custom:
            return self.async_abort(reason="no_custom_datapoints")

        if user_input is not None:
            for key in user_input.get("datapoints", []):
                custom.pop(key, None)
            options = {**self.config_entry.options, CONF_CUSTOM_DATAPOINTS: custom}
            return self.async_create_entry(data=options)

        choices = [
            SelectOptionDict(
                value=key,
                label=f"{config.get('name') or key} (id {key})",
            )
            for key, config in custom.items()
        ]
        return self.async_show_form(
            step_id=MENU_REMOVE_DATAPOINT,
            data_schema=vol.Schema(
                {
                    vol.Required("datapoints"): SelectSelector(
                        SelectSelectorConfig(
                            options=choices,
                            multiple=True,
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )
