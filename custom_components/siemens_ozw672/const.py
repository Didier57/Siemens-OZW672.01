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
CONF_DISABLED_DATAPOINTS: Final = "disabled_datapoints"
CONF_DEVICE_ID: Final = "device_id"
CONF_DEVICE_NAME: Final = "device_name"
CONF_GATEWAY_SERIAL: Final = "gateway_serial"
CONF_GATEWAY_FIRMWARE: Final = "gateway_firmware"

PLATFORM_SENSOR: Final = "sensor"
PLATFORM_NUMBER: Final = "number"
PLATFORM_SELECT: Final = "select"

TYPE_NUMERIC: Final = "Numeric"
TYPE_ENUMERATION: Final = "Enumeration"

SELECTOR_VALUE_TYPE_NUMERIC: Final = "numeric"
SELECTOR_VALUE_TYPE_ENUMERATION: Final = "enumeration"
VALUE_TYPE_SELECTOR_TO_API: Final = {
    SELECTOR_VALUE_TYPE_NUMERIC: TYPE_NUMERIC,
    SELECTOR_VALUE_TYPE_ENUMERATION: TYPE_ENUMERATION,
}

SERVICE_WRITE_DATAPOINT: Final = "write_datapoint"
ATTR_DATAPOINT_ID: Final = "datapoint_id"
ATTR_VALUE: Final = "value"
ATTR_VALUE_TYPE: Final = "value_type"

# Values that mean "the controller has no value for this datapoint" (the
# datapoint exists on the bus but no sensor/module is wired to it).
INVALID_TOKENS: Final[frozenset[str]] = frozenset({"----", "---", "--", "-", "!"})


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


# Datapoint identifiers are built by the OZW672 for the plant it is connected
# to, so they differ from one installation to the next. The catalog below was
# read from a real installation (OZW672.01 + RVS21.831F/127 heat pump
# controller) and is used as a starting point: extra datapoints can be declared
# in the integration options and datapoints that do not exist on another plant
# can be disabled there.
DATAPOINTS: Final[tuple[Datapoint, ...]] = (
    # --- Temperatures -----------------------------------------------------
    Datapoint(
        id=15191,
        key="outside_temperature",
        name="Outside temperature",
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
    Datapoint(
        id=15148,
        key="room_temperature",
        name="Room temperature",
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
    Datapoint(
        id=15149,
        key="room_setpoint",
        name="Active room setpoint",
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
    Datapoint(
        id=15150,
        key="flow_temperature",
        name="Flow temperature heating circuit 1",
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
    Datapoint(
        id=15151,
        key="flow_setpoint",
        name="Flow setpoint heating circuit 1",
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
    Datapoint(
        id=15129,
        key="heat_pump_flow_temperature",
        name="Heat pump flow temperature",
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
    Datapoint(
        id=15127,
        key="heat_pump_return_temperature",
        name="Heat pump return temperature",
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
    Datapoint(
        id=15160,
        key="dhw_temperature",
        name="DHW temperature top",
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
    Datapoint(
        id=15162,
        key="dhw_temperature_bottom",
        name="DHW temperature bottom",
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
    Datapoint(
        id=15161,
        key="dhw_setpoint",
        name="Active DHW setpoint",
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
    # --- Other measurements ----------------------------------------------
    Datapoint(
        id=15196,
        key="hydraulic_pressure",
        name="Hydraulic pressure",
        unit="bar",
        device_class="pressure",
        state_class="measurement",
    ),
    Datapoint(
        id=15130,
        key="compressor_modulation",
        name="Compressor modulation",
        unit="%",
        state_class="measurement",
    ),
    Datapoint(
        id=15243,
        key="thermal_energy",
        name="Thermal energy",
        unit="kWh",
        device_class="energy",
        state_class="total_increasing",
    ),
    Datapoint(
        id=15133,
        key="compressor_hours",
        name="Compressor operating hours",
        unit="h",
        device_class="duration",
        state_class="total_increasing",
    ),
    Datapoint(
        id=15163,
        key="dhw_pump_hours",
        name="DHW pump operating hours",
        unit="h",
        device_class="duration",
        state_class="total_increasing",
    ),
    # --- States (text) ---------------------------------------------------
    Datapoint(
        id=15220,
        key="heat_pump_state",
        name="Heat pump state",
        value_type=TYPE_ENUMERATION,
    ),
    Datapoint(
        id=15122,
        key="compressor_state",
        name="Compressor state",
        value_type=TYPE_ENUMERATION,
    ),
    Datapoint(
        id=14951,
        key="dhw_state",
        name="DHW state",
        value_type=TYPE_ENUMERATION,
    ),
    Datapoint(
        id=14949,
        key="heating_circuit_state",
        name="Heating circuit 1 state",
        value_type=TYPE_ENUMERATION,
    ),
    Datapoint(
        id=14407,
        key="dhw_mode",
        name="DHW mode",
        value_type=TYPE_ENUMERATION,
    ),
    Datapoint(
        id=14410,
        key="dhw_release",
        name="DHW release",
        value_type=TYPE_ENUMERATION,
    ),
    Datapoint(
        id=14388,
        key="cooling_circuit_mode",
        name="Cooling circuit 1 mode",
        value_type=TYPE_ENUMERATION,
    ),
    Datapoint(
        id=14624,
        key="fault_message",
        name="Fault message",
        value_type=TYPE_ENUMERATION,
    ),
    Datapoint(
        id=15208,
        key="maintenance_message",
        name="Maintenance message",
        value_type=TYPE_ENUMERATION,
    ),
    # --- Writable setpoints ----------------------------------------------
    Datapoint(
        id=14408,
        key="dhw_setpoint_normal",
        name="DHW setpoint normal",
        platform=PLATFORM_NUMBER,
        unit="°C",
        device_class="temperature",
        min_value=10.0,
        max_value=80.0,
        step=0.5,
    ),
    Datapoint(
        id=14409,
        key="dhw_setpoint_reduced",
        name="DHW setpoint reduced",
        platform=PLATFORM_NUMBER,
        unit="°C",
        device_class="temperature",
        min_value=10.0,
        max_value=80.0,
        step=0.5,
    ),
    Datapoint(
        id=14389,
        key="cooling_comfort_setpoint",
        name="Cooling comfort setpoint",
        platform=PLATFORM_NUMBER,
        unit="°C",
        device_class="temperature",
        min_value=5.0,
        max_value=35.0,
        step=0.5,
    ),
)
