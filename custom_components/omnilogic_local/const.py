"""Constants for the OmniLogic Local integration."""
from enum import Enum
from typing import Final

from pyomnilogic_local.types import OmniType

# from homeassistant.backports.enum import StrEnum

DOMAIN: Final[str] = "omnilogic_local"
KEY_COORDINATOR: Final[str] = "coordinator"
KEY_OMNI_API: Final[str] = "omni_api"
KEY_DEVICE_REGISTRY: Final[str] = "device_registry"
DEFAULT_POLL_INTERVAL: Final[int] = 20

# According to Hayward docs, the backyard always has a system id of 0
BACKYARD_SYSTEM_ID: Final[int] = 0

UNIQUE_ID: Final[str] = "omnilogic"
MANUFACTURER: Final[str] = "Hayward"

KEY_MSP_SYSTEM_ID: Final[str] = "System_Id"
KEY_TELEMETRY_SYSTEM_ID: Final[str] = "@systemId"


class OmniModel(str, Enum):
    BOW_POOL = "BOW_POOL"
    BOW_SPA = "BOW_SPA"
    RELAY_LOW_VOLTAGE = "RLY_LOW_VOLTAGE_RELAY"
    RELAY_HIGH_VOLTAGE = "RLY_HIGH_VOLTAGE_RELAY"
    RELAY_VALVE_ACTUATOR = "RLY_VALVE_ACTUATOR"
    SENSOR_AIR = "SENSOR_AIR_TEMP"
    SENSOR_FLOW = "SENSOR_FLOW"
    SENSOR_WATER = "SENSOR_WATER_TEMP"
    SENSOR_SOLAR = "SENSOR_SOLAR_TEMP"
    SINGLE_SPEED_PUMP = "PMP_SINGLE_SPEED"
    VARIABLE_SPEED_PUMP = "PMP_VARIABLE_SPEED_PUMP"
    SINGLE_SPEED_FILTER = "FMT_SINGLE_SPEED"
    DUAL_SPEED_FILTER = "FMT_DUAL_SPEED"
    VARIABLE_SPEED_FILTER = "FMT_VARIABLE_SPEED_PUMP"
    LIGHT_CL_UCL = "COLOR_LOGIC_UCL"
    LIGHT_CL_2_5 = "COLOR_LOGIC_2_5"
    LIGHT_CL_4_0 = "COLOR_LOGIC_2_5"


OMNI_TO_HASS_TYPES: dict[str, str] = {
    OmniType.BACKYARD: "device",
    OmniType.BOW: "device",
    OmniType.BOW_MSP: "device",
    OmniType.CHLORINATOR: "switch",
    OmniType.CHLORINATOR_EQUIP: "switch",
    OmniType.CL_LIGHT: "light",
    OmniType.FILTER: "switch",
    OmniType.HEATER: "water_heater",
    OmniType.HEATER_EQUIP: "water_heater",
    OmniType.PUMP: "switch",
    OmniType.RELAY: "switch",
    OmniType.SENSOR: "sensor",
    OmniType.VALVE_ACTUATOR: "switch",
    OmniType.VIRT_HEATER: "water_heater",
}


class OmniRelayFunction(str, Enum):
    WATER_FEATURE = "RLY_WATER_FEATURE"
    WATERFALL = "RLY_WATERFALL"
    FOUNTAIN = "RLY_FOUNTAIN"


OMNI_TYPES = [k.value for k in OmniType]
OMNI_TYPES_BOW = [OmniModel.BOW_POOL, OmniModel.BOW_SPA]
OMNI_TYPES_PUMP = [OmniType.FILTER, OmniType.PUMP]
OMNI_TYPES_LIGHT: Final[list[str]] = [k for k, v in OMNI_TO_HASS_TYPES.items() if v == "light"]
OMNI_TYPES_SWITCH: Final[list[str]] = [k for k, v in OMNI_TO_HASS_TYPES.items() if v == "switch"]
OMNI_TYPES_SENSOR: Final[list[str]] = [k for k, v in OMNI_TO_HASS_TYPES.items() if v == "sensor"]
OMNI_TYPES_WATER_HEATER: Final[list[str]] = [k for k, v in OMNI_TO_HASS_TYPES.items() if v == "water_heater"]
