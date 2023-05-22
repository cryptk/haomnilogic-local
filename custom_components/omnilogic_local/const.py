"""Constants for the OmniLogic Local integration."""
from enum import Enum
from typing import Final

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
    BOW_POOL: Final[str] = "BOW_POOL"
    BOW_SPA: Final[str] = "BOW_SPA"
    RELAY_LOW_VOLTAGE: Final[str] = "RLY_LOW_VOLTAGE_RELAY"
    RELAY_HIGH_VOLTAGE: Final[str] = "RLY_HIGH_VOLTAGE_RELAY"
    RELAY_VALVE_ACTUATOR: Final[str] = "RLY_VALVE_ACTUATOR"
    SENSOR_AIR: Final[str] = "SENSOR_AIR_TEMP"
    SENSOR_FLOW: Final[str] = "SENSOR_FLOW"
    SENSOR_WATER: Final[str] = "SENSOR_WATER_TEMP"
    SENSOR_SOLAR: Final[str] = "SENSOR_SOLAR_TEMP"
    SINGLE_SPEED_PUMP: Final[str] = "PMP_SINGLE_SPEED"
    VARIABLE_SPEED_PUMP: Final[str] = "PMP_VARIABLE_SPEED_PUMP"
    SINGLE_SPEED_FILTER: Final[str] = "FMT_SINGLE_SPEED"
    DUAL_SPEED_FILTER: Final[str] = "FMT_DUAL_SPEED"
    VARIABLE_SPEED_FILTER: Final[str] = "FMT_VARIABLE_SPEED_PUMP"
    LIGHT_CL_UCL: Final[str] = "COLOR_LOGIC_UCL"
    LIGHT_CL_2_5: Final[str] = "COLOR_LOGIC_2_5"
    LIGHT_CL_4_0: Final[str] = "COLOR_LOGIC_2_5"


class OmniType(str, Enum):
    BACKYARD: Final[str] = "Backyard"
    BOW: Final[str] = "BodyOfWater"
    BOW_MSP: Final[str] = "Body_of_water"
    CHLORINATOR: Final[str] = "Chlorinator"
    CHLORINATOR_EQUIP: Final[str] = "Chlorinator_Equipment"
    CL_LIGHT: Final[str] = "ColorLogic_Light"
    FILTER: Final[str] = "Filter"
    GROUP: Final[str] = "Group"
    HEATER: Final[str] = "Heater"
    HEATER_EQUIP: Final[str] = "Heater_Equipment"
    PUMP: Final[str] = "Pump"
    RELAY: Final[str] = "Relay"
    SENSOR: Final[str] = "Sensor"
    VALVE_ACTUATOR: Final[str] = "ValveActuator"
    VIRT_HEATER: Final[str] = "VirtualHeater"


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
    WATER_FEATURE: Final[str] = "RLY_WATER_FEATURE"
    WATERFALL: Final[str] = "RLY_WATERFALL"
    FOUNTAIN: Final[str] = "RLY_FOUNTAIN"


class OmniColorLogicLightType(str, Enum):
    UCL: Final[str] = "COLOR_LOGIC_UCL"
    FOUR_ZERO: Final[str] = "COLOR_LOGIC_4_0"
    TWO_FIVE: Final[str] = "COLOR_LOGIC_2_5"


OMNI_TYPES = [k.value for k in OmniType]
OMNI_TYPES_BOW = [OmniModel.BOW_POOL, OmniModel.BOW_SPA]
OMNI_TYPES_PUMP = [OmniType.FILTER, OmniType.PUMP]
OMNI_TYPES_LIGHT: Final[list[str]] = [k for k, v in OMNI_TO_HASS_TYPES.items() if v == "light"]
OMNI_TYPES_SWITCH: Final[list[str]] = [k for k, v in OMNI_TO_HASS_TYPES.items() if v == "switch"]
OMNI_TYPES_SENSOR: Final[list[str]] = [k for k, v in OMNI_TO_HASS_TYPES.items() if v == "sensor"]
OMNI_TYPES_WATER_HEATER: Final[list[str]] = [k for k, v in OMNI_TO_HASS_TYPES.items() if v == "water_heater"]
