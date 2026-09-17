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
    CONF_DATAPOINTS,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_GATEWAY_FIRMWARE,
    CONF_GATEWAY_SERIAL,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USE_HTTPS,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
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
    guess_device_class,
    guess_state_class,
)

_LOGGER = logging.getLogger(__name__)

MENU_ADD_DATAPOINTS = "add_datapoints"
MENU_REMOVE_DATAPOINTS = "remove_datapoints"
MENU_EDIT_DATAPOINT = "edit_datapoint"
MENU_SETTINGS = "settings"
MENU_FINISH = "finish"
MENU_NEXT_TOPIC = "next_topic"
MENU_PREVIOUS_TOPIC = "previous_topic"

DATAPOINTS_FIELD = "datapoints"
KEY_FIELD = "key"
ENUM_OPTIONS_FIELD = "enum_options"

ROOT_TOPIC_LABEL = "(root)"


def datapoint_key(config: dict[str, Any]) -> str:
    """Return the stable storage key of a datapoint configuration."""
    return str(config.get(DP_PATH) or f"id:{config.get(DP_ID)}")


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


async def _async_walk(
    hass: HomeAssistant, data: dict[str, Any], device_id: int
) -> list[dict[str, Any]]:
    """Enumerate every datapoint of a device with its topic path."""
    client = _client(hass, data)
    await client.async_login()
    try:
        return await client.async_walk_datapoints(device_id)
    finally:
        await client.async_logout()


async def _async_describe(
    hass: HomeAssistant, data: dict[str, Any], datapoint_ids: list[int]
) -> dict[int, dict[str, Any]]:
    """Read the type and the unit of freshly selected datapoints."""
    details: dict[int, dict[str, Any]] = {
        datapoint_id: {} for datapoint_id in datapoint_ids
    }
    if not datapoint_ids:
        return details

    client = _client(hass, data)
    await client.async_login()
    try:
        for datapoint_id in datapoint_ids:
            try:
                details[datapoint_id] = await client.async_read_datapoint_details(
                    datapoint_id
                )
            except OZW672Error as err:
                _LOGGER.warning("Cannot read datapoint %s: %s", datapoint_id, err)
    finally:
        await client.async_logout()
    return details


def _topic_of(path: str) -> str:
    """Return the topic a datapoint path belongs to."""
    return path.rsplit("/", 1)[0] if "/" in path else ROOT_TOPIC_LABEL


def _group_topics(walk: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group the enumerated datapoints by their topic."""
    topics: dict[str, list[dict[str, Any]]] = {}
    for item in walk:
        topics.setdefault(_topic_of(str(item.get(DP_PATH) or "")), []).append(item)
    return topics


def _datapoint_selector(items: list[dict[str, Any]]) -> SelectSelector:
    """Build a multi-select listing the datapoints of one topic."""
    options = [
        SelectOptionDict(
            value=str(item.get(DP_PATH)),
            label=f"{item.get(DP_NAME)}  [{item.get(DP_ID)}]",
        )
        for item in items
    ]
    return SelectSelector(
        SelectSelectorConfig(
            options=options, multiple=True, mode=SelectSelectorMode.LIST
        )
    )


def _ordered_topics(walk: list[dict[str, Any]]) -> list[str]:
    """Return the topics of a plant in menu tree order."""
    return list(_group_topics(walk))


def _selected_paths(
    items: list[dict[str, Any]], datapoints: dict[str, Any]
) -> list[str]:
    """Return the paths of a topic that are already configured."""
    return [
        str(item.get(DP_PATH)) for item in items if datapoint_key(item) in datapoints
    ]


async def _async_apply_topic(
    hass: HomeAssistant,
    data: dict[str, Any],
    datapoints: dict[str, Any],
    items: list[dict[str, Any]],
    chosen: set[str],
) -> None:
    """Store the datapoints chosen for one topic.

    Datapoints that are already configured keep their settings; newly ticked
    ones are described by the device to guess their type and unit, and the
    ones that were unticked are removed.
    """
    missing = [
        int(item[DP_ID])
        for item in items
        if str(item.get(DP_PATH)) in chosen and datapoint_key(item) not in datapoints
    ]
    details = await _async_describe(hass, data, missing)
    for item in items:
        key = datapoint_key(item)
        if str(item.get(DP_PATH)) in chosen:
            if key not in datapoints:
                datapoints[key] = _build_datapoint(
                    item, details.get(int(item[DP_ID]), {})
                )
        else:
            datapoints.pop(key, None)


def _build_datapoint(item: dict[str, Any], details: dict[str, Any]) -> dict[str, Any]:
    """Turn a menu tree entry into a stored datapoint configuration.

    The device only tells us the value type and the unit of a datapoint, not
    whether it is meant to be a setpoint: writable numeric datapoints are
    exposed as numbers, everything else (enumerations, radio buttons, time of
    day) is exposed as a text sensor. The platform can be changed afterwards
    in the options.
    """
    datapoint_id = int(item[DP_ID])
    value_type = str(details.get("type") or TYPE_NUMERIC)
    unit = details.get("unit") or None
    write_access = bool(item.get(DP_WRITE_ACCESS))
    platform = (
        PLATFORM_NUMBER
        if write_access and value_type == TYPE_NUMERIC
        else PLATFORM_SENSOR
    )

    device_class = guess_device_class(unit)
    if platform == PLATFORM_NUMBER:
        state_class = None
        min_value: float | None = 0.0
        max_value: float | None = 100.0
        step: float | None = 0.5
    else:
        state_class = guess_state_class(unit) if value_type == TYPE_NUMERIC else None
        min_value = max_value = step = None

    return {
        DP_ID: datapoint_id,
        DP_NAME: str(item.get(DP_NAME) or f"Datapoint {datapoint_id}"),
        DP_PATH: item.get(DP_PATH),
        DP_ADDRESS: item.get(DP_ADDRESS),
        DP_SUBKEY: item.get(DP_SUBKEY),
        DP_WRITE_ACCESS: write_access,
        DP_PLATFORM: platform,
        DP_VALUE_TYPE: value_type,
        DP_UNIT: unit,
        DP_DEVICE_CLASS: device_class,
        DP_STATE_CLASS: state_class,
        DP_OPTIONS: None,
        DP_MIN_VALUE: min_value,
        DP_MAX_VALUE: max_value,
        DP_STEP: step,
    }


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


def _format_enum_options(options: Any) -> str:
    """Render a stored enumeration mapping as '1=Label, 2=Label'."""
    if not isinstance(options, dict):
        return ""
    return ", ".join(f"{key}={label}" for key, label in options.items())


def _selector_value_type(value_type: str | None) -> str:
    """Return the selector value matching a device value type."""
    if value_type == TYPE_ENUMERATION:
        return SELECTOR_VALUE_TYPE_ENUMERATION
    return SELECTOR_VALUE_TYPE_NUMERIC


def _datapoint_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Build the schema used to describe or edit a datapoint."""
    defaults = defaults or {}

    def number_field(key: str) -> vol.Marker:
        if defaults.get(key) is None:
            return vol.Optional(key)
        return vol.Optional(key, description={"suggested_value": defaults[key]})

    return vol.Schema(
        {
            vol.Required(DP_NAME, default=defaults.get(DP_NAME, "")): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Required(
                DP_PLATFORM, default=defaults.get(DP_PLATFORM, PLATFORM_SENSOR)
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[PLATFORM_SENSOR, PLATFORM_NUMBER, PLATFORM_SELECT],
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="platform",
                )
            ),
            vol.Required(
                DP_VALUE_TYPE,
                default=_selector_value_type(defaults.get(DP_VALUE_TYPE)),
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
            vol.Optional(DP_UNIT, default=defaults.get(DP_UNIT) or ""): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Optional(
                DP_DEVICE_CLASS, default=defaults.get(DP_DEVICE_CLASS) or ""
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Optional(
                DP_STATE_CLASS, default=defaults.get(DP_STATE_CLASS) or ""
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Optional(
                ENUM_OPTIONS_FIELD,
                default=_format_enum_options(defaults.get(DP_OPTIONS)),
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            number_field(DP_MIN_VALUE): NumberSelector(
                NumberSelectorConfig(mode=NumberSelectorMode.BOX, step="any")
            ),
            number_field(DP_MAX_VALUE): NumberSelector(
                NumberSelectorConfig(mode=NumberSelectorMode.BOX, step="any")
            ),
            number_field(DP_STEP): NumberSelector(
                NumberSelectorConfig(mode=NumberSelectorMode.BOX, step="any")
            ),
        }
    )


def _apply_datapoint_form(
    config: dict[str, Any], user_input: dict[str, Any]
) -> dict[str, Any]:
    """Merge an (edited) datapoint form into a stored configuration."""
    enum_options = _parse_enum_options(user_input.get(ENUM_OPTIONS_FIELD))
    platform = user_input[DP_PLATFORM]
    if enum_options and platform == PLATFORM_SENSOR:
        platform = PLATFORM_SELECT
    value_type = VALUE_TYPE_SELECTOR_TO_API.get(
        str(user_input[DP_VALUE_TYPE]), TYPE_NUMERIC
    )
    updated = dict(config)
    updated.update(
        {
            DP_NAME: user_input[DP_NAME],
            DP_PLATFORM: platform,
            DP_VALUE_TYPE: (
                TYPE_ENUMERATION
                if enum_options or value_type == TYPE_ENUMERATION
                else value_type
            ),
            DP_UNIT: user_input.get(DP_UNIT) or None,
            DP_DEVICE_CLASS: user_input.get(DP_DEVICE_CLASS) or None,
            DP_STATE_CLASS: user_input.get(DP_STATE_CLASS) or None,
            DP_OPTIONS: {str(key): label for key, label in enum_options.items()}
            if enum_options
            else None,
            DP_MIN_VALUE: user_input.get(DP_MIN_VALUE),
            DP_MAX_VALUE: user_input.get(DP_MAX_VALUE),
            DP_STEP: user_input.get(DP_STEP),
        }
    )
    return updated


class SiemensOZW672ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the configuration flow."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialise the flow."""
        self._reauth_entry: ConfigEntry | None = None
        self._connection: dict[str, Any] = {}
        self._devices: list[dict[str, Any]] = []
        self._gateway: dict[str, Any] = {}
        self._walk: list[dict[str, Any]] = []
        self._selection: dict[str, dict[str, Any]] = {}
        self._device_id: int | None = None
        self._device_name: str | None = None
        self._topics: list[str] = []
        self._topic_index: int = 0

    def _async_create_entry(self) -> FlowResult:
        """Create the config entry for the connection and the chosen device."""
        data = dict(self._connection)
        firmware = self._gateway.get("FwVersion")
        serial = self._gateway.get("SerialNr")
        if firmware:
            data[CONF_GATEWAY_FIRMWARE] = str(firmware)
        if serial:
            data[CONF_GATEWAY_SERIAL] = str(serial)
        if self._device_id is not None:
            data[CONF_DEVICE_ID] = int(self._device_id)
        if self._device_name:
            data[CONF_DEVICE_NAME] = self._device_name
        title = self._device_name or data[CONF_HOST]
        return self.async_create_entry(
            title=title,
            data=data,
            options={
                CONF_DATAPOINTS: self._selection,
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            },
        )

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
        depend on the plant, so the menu tree of the selected controller is
        read to enumerate the datapoints it provides.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            raw_id = int(user_input[CONF_DEVICE_ID])
            name = next(
                (device["name"] for device in self._devices if device["id"] == raw_id),
                None,
            )
            try:
                walk = await _async_walk(self.hass, self._connection, raw_id)
            except OZW672Error as err:
                _LOGGER.error("Cannot read the OZW672 menu tree: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error while reading the OZW672 tree")
                errors["base"] = "unknown"
            else:
                if not walk:
                    errors["base"] = "no_datapoints"
                else:
                    self._device_id = raw_id
                    self._device_name = name
                    self._walk = walk
                    return await self.async_step_datapoints()

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
            errors=errors,
        )

    async def async_step_datapoints(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the datapoint selection menu."""
        return self.async_show_menu(
            step_id="datapoints",
            menu_options=[MENU_ADD_DATAPOINTS, MENU_FINISH],
        )

    def _current_topic(self) -> str:
        """Return the topic being browsed."""
        if not self._topics:
            return ""
        index = min(max(self._topic_index, 0), len(self._topics) - 1)
        return self._topics[index]

    async def _async_show_topic(self) -> FlowResult:
        """Show the datapoints of the topic being browsed."""
        topic = self._current_topic()
        items = _group_topics(self._walk).get(topic, [])
        return self.async_show_form(
            step_id="pick",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        DATAPOINTS_FIELD,
                        default=_selected_paths(items, self._selection),
                    ): _datapoint_selector(items)
                }
            ),
            description_placeholders={
                "topic": topic,
                "index": str(self._topic_index + 1),
                "total": str(len(self._topics)),
            },
        )

    async def async_step_topic_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Offer to browse the next topic or to finish.

        Home Assistant requires the step id of a returned menu to have a
        matching ``async_step_<step_id>`` method, so the menu is returned by
        this step, which ``async_step_pick`` reaches after storing a topic.
        """
        menu: list[str] = []
        if self._topic_index < len(self._topics) - 1:
            menu.append(MENU_NEXT_TOPIC)
        if self._topic_index > 0:
            menu.append(MENU_PREVIOUS_TOPIC)
        menu.append(MENU_FINISH)
        return self.async_show_menu(step_id="topic_menu", menu_options=menu)

    async def async_step_add_datapoints(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Browse the topics of the plant one after the other."""
        self._topics = _ordered_topics(self._walk)
        self._topic_index = 0
        if not self._topics:
            return self._async_create_entry()
        return await self._async_show_topic()

    async def async_step_next_topic(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Browse the next topic."""
        self._topic_index += 1
        return await self._async_show_topic()

    async def async_step_previous_topic(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Browse the previous topic."""
        self._topic_index = max(self._topic_index - 1, 0)
        return await self._async_show_topic()

    async def async_step_pick(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Store the datapoints chosen for the topic being browsed."""
        if user_input is not None:
            items = _group_topics(self._walk).get(self._current_topic(), [])
            chosen = {str(path) for path in user_input.get(DATAPOINTS_FIELD) or []}
            await _async_apply_topic(
                self.hass, self._connection, self._selection, items, chosen
            )
            return await self.async_step_topic_menu()
        return await self._async_show_topic()

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Create the entry with the selected datapoints."""
        return self._async_create_entry()

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

    def __init__(self) -> None:
        """Initialise the flow."""
        self._walk: list[dict[str, Any]] = []
        self._topics: list[str] = []
        self._topic_index: int = 0
        self._working: dict[str, Any] | None = None
        self._edit_key: str = ""

    @property
    def _datapoints(self) -> dict[str, Any]:
        """Return the datapoints being edited, as a working copy."""
        if self._working is None:
            self._working = dict(self.config_entry.options.get(CONF_DATAPOINTS) or {})
        return self._working

    def _save(self) -> FlowResult:
        """Write the datapoints back into the options."""
        options = {**self.config_entry.options, CONF_DATAPOINTS: self._datapoints}
        return self.async_create_entry(data=options)

    def _current_topic(self) -> str:
        """Return the topic being browsed."""
        if not self._topics:
            return ""
        index = min(max(self._topic_index, 0), len(self._topics) - 1)
        return self._topics[index]

    async def _async_show_topic(self) -> FlowResult:
        """Show the datapoints of the topic being browsed."""
        topic = self._current_topic()
        items = _group_topics(self._walk).get(topic, [])
        return self.async_show_form(
            step_id="pick",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        DATAPOINTS_FIELD,
                        default=_selected_paths(items, self._datapoints),
                    ): _datapoint_selector(items)
                }
            ),
            description_placeholders={
                "topic": topic,
                "index": str(self._topic_index + 1),
                "total": str(len(self._topics)),
            },
        )

    async def async_step_topic_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Offer to browse the next topic or to save.

        Home Assistant requires the step id of a returned menu to have a
        matching ``async_step_<step_id>`` method, so the menu is returned by
        this step, which ``async_step_pick`` reaches after storing a topic.
        """
        menu: list[str] = []
        if self._topic_index < len(self._topics) - 1:
            menu.append(MENU_NEXT_TOPIC)
        if self._topic_index > 0:
            menu.append(MENU_PREVIOUS_TOPIC)
        menu.append(MENU_FINISH)
        return self.async_show_menu(step_id="topic_menu", menu_options=menu)

    async def _async_walk_tree(self) -> None:
        """Read the menu tree of the configured controller."""
        try:
            self._walk = await _async_walk(
                self.hass,
                dict(self.config_entry.data),
                int(self.config_entry.data[CONF_DEVICE_ID]),
            )
        except OZW672Error as err:
            _LOGGER.error("Cannot read the OZW672 menu tree: %s", err)
            self._walk = []

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the options menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                MENU_SETTINGS,
                MENU_ADD_DATAPOINTS,
                MENU_REMOVE_DATAPOINTS,
                MENU_EDIT_DATAPOINT,
            ],
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Update the polling interval."""
        if user_input is not None:
            options = {
                **self.config_entry.options,
                **user_input,
                CONF_DATAPOINTS: self._datapoints,
            }
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

    async def async_step_add_datapoints(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Browse the topics of the plant one after the other."""
        if not self._walk:
            await self._async_walk_tree()
        if not self._walk:
            return self.async_show_form(
                step_id=MENU_ADD_DATAPOINTS,
                data_schema=vol.Schema({}),
                errors={"base": "cannot_connect"},
            )

        self._topics = _ordered_topics(self._walk)
        self._topic_index = 0
        return await self._async_show_topic()

    async def async_step_next_topic(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Browse the next topic."""
        self._topic_index += 1
        return await self._async_show_topic()

    async def async_step_previous_topic(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Browse the previous topic."""
        self._topic_index = max(self._topic_index - 1, 0)
        return await self._async_show_topic()

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Save the datapoints and close the options."""
        return self._save()

    async def async_step_pick(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Store the datapoints chosen for the topic being browsed."""
        if user_input is not None:
            items = _group_topics(self._walk).get(self._current_topic(), [])
            chosen = {str(path) for path in user_input.get(DATAPOINTS_FIELD) or []}
            await _async_apply_topic(
                self.hass,
                dict(self.config_entry.data),
                self._datapoints,
                items,
                chosen,
            )
            return await self.async_step_topic_menu()
        return await self._async_show_topic()

    async def async_step_remove_datapoints(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove datapoints from the entry."""
        datapoints = self._datapoints
        if not datapoints:
            return self.async_abort(reason="no_datapoints")

        if user_input is not None:
            for key in user_input.get(DATAPOINTS_FIELD, []):
                datapoints.pop(key, None)
            return self._save()

        options_list = [
            SelectOptionDict(
                value=key,
                label=f"{config.get(DP_NAME) or key}  [{config.get(DP_ID)}]",
            )
            for key, config in datapoints.items()
        ]
        return self.async_show_form(
            step_id=MENU_REMOVE_DATAPOINTS,
            data_schema=vol.Schema(
                {
                    vol.Required(DATAPOINTS_FIELD): SelectSelector(
                        SelectSelectorConfig(
                            options=options_list,
                            multiple=True,
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    async def async_step_edit_datapoint(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select the datapoint to edit."""
        datapoints = self._datapoints
        if not datapoints:
            return self.async_abort(reason="no_datapoints")

        if user_input is not None:
            self._edit_key = str(user_input[KEY_FIELD])
            return await self.async_step_edit_datapoint_form()

        options_list = [
            SelectOptionDict(
                value=key,
                label=f"{config.get(DP_NAME) or key}  [{config.get(DP_ID)}]",
            )
            for key, config in datapoints.items()
        ]
        return self.async_show_form(
            step_id=MENU_EDIT_DATAPOINT,
            data_schema=vol.Schema(
                {
                    vol.Required(KEY_FIELD): SelectSelector(
                        SelectSelectorConfig(
                            options=options_list, mode=SelectSelectorMode.DROPDOWN
                        )
                    )
                }
            ),
        )

    async def async_step_edit_datapoint_form(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit the metadata of a datapoint."""
        datapoints = self._datapoints
        key = self._edit_key
        config = datapoints.get(key)
        if config is None:
            return self.async_abort(reason="no_datapoints")

        if user_input is not None:
            datapoints[key] = _apply_datapoint_form(config, user_input)
            return self._save()

        return self.async_show_form(
            step_id="edit_datapoint_form",
            data_schema=_datapoint_schema(config),
            description_placeholders={"path": str(config.get(DP_PATH) or "")},
        )
