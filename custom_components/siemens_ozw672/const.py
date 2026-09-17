"""Constants for the Siemens OZW672 integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

DOMAIN: Final = "siemens_ozw672"
MANUFACTURER: Final = "Siemens"
MODEL: Final = "OZW672.01"

DEFAULT_PORT: Final = 80
DEFAULT_HTTPS_PORT: Final = 443
DEFAULT_SCAN_INTERVAL: Final = 60
MIN_SCAN_INTERVAL: Final = 10
MAX_SCAN_INTERVAL: Final = 3600

CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_USE_HTTPS: Final = "use_https"
CONF_VERIFY_SSL: Final = "verify_ssl"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_CUSTOM_DATAPOINTS: Final = "custom_datapoints"

PLATFORM_SENSOR: Final = "sensor"
PLATFORM_NUMBER: Final = "number"
PLATFORM_SELECT: Final = "select"

TYPE_NUMERIC: Final = "Numeric"
TYPE_ENUMERATION: Final = "Enumeration"

SERVICE_WRITE_DATAPOINT: Final = "write_datapoint"
ATTR_DATAPOINT_ID: Final = "datapoint_id"
ATTR_VALUE: Final = "value"
ATTR_VALUE_TYPE: Final = "value_type"

OPERATING_MODES: Final[dict[int, str]] = {
    1: "Automatic",
    2: "Reduced",
    3: "Comfort",
}


@dataclass(frozen=True, kw_only=True)
class Datapoint:
    """Description of a single OZW672 datapoint."""

    id: int
    key: str
    name: str
    platform: str = PLATFORM_SENSOR
    value_type: str = TYPE_NUMERIC
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = None
    options: dict[int, str] | None = None
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    custom: bool = False


DATAPOINTS: Final[tuple[Datapoint, ...]] = (
    Datapoint(
        id=2686,
        key="operating_mode",
        name="Operating mode",
        platform=PLATFORM_SELECT,
        value_type=TYPE_ENUMERATION,
        options=OPERATING_MODES,
    ),
    Datapoint(
        id=2687,
        key="comfort_setpoint",
        name="Comfort setpoint",
        platform=PLATFORM_NUMBER,
        unit="°C",
        device_class="temperature",
        min_value=5.0,
        max_value=35.0,
        step=0.5,
    ),
    Datapoint(
        id=2688,
        key="reduced_setpoint",
        name="Reduced setpoint",
        platform=PLATFORM_NUMBER,
        unit="°C",
        device_class="temperature",
        min_value=5.0,
        max_value=35.0,
        step=0.5,
    ),
    Datapoint(
        id=2690,
        key="heating_curve",
        name="Heating curve slope",
        platform=PLATFORM_NUMBER,
        min_value=0.2,
        max_value=3.5,
        step=0.1,
    ),
    Datapoint(
        id=3059,
        key="boiler_state",
        name="Boiler state",
        value_type=TYPE_ENUMERATION,
    ),
    Datapoint(
        id=3062,
        key="burner_state",
        name="Burner state",
        value_type=TYPE_ENUMERATION,
    ),
    Datapoint(
        id=3068,
        key="boiler_temperature",
        name="Boiler temperature",
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
    Datapoint(
        id=3074,
        key="return_temperature",
        name="Return temperature",
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
    Datapoint(
        id=3078,
        key="burner_modulation",
        name="Burner modulation",
        unit="%",
        state_class="measurement",
    ),
    Datapoint(
        id=3198,
        key="fault_message",
        name="Fault message",
        value_type=TYPE_ENUMERATION,
    ),
    Datapoint(
        id=3209,
        key="room_temperature",
        name="Room temperature",
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
    Datapoint(
        id=3212,
        key="outside_temperature",
        name="Outside temperature",
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
    Datapoint(
        id=3215,
        key="dhw_temperature",
        name="DHW temperature",
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
)
