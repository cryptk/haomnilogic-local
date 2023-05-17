"""Constants for the OmniLogic Local integration."""
from enum import Enum
from typing import Final

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


class OmniModels(str, Enum):
    RELAY_HIGH_VOLTAGE = "RLY_HIGH_VOLTAGE_RELAY"
    RELAY_VALVE_ACTUATOR = "RLY_VALVE_ACTUATOR"
    VARIABLE_SPEED_FILTER = "FMT_VARIABLE_SPEED_PUMP"
    VARIABLE_SPEED_PUMP = "PMP_VARIABLE_SPEED_PUMP"
    BOW_POOL = "BOW_POOL"
    BOW_SPA = "BOW_SPA"


class OmniTypes(str, Enum):
    BACKYARD: Final[str] = "Backyard"
    BOW: Final[str] = "BodyOfWater"
    BOW_MSP: Final[str] = "Body_of_water"
    CL_LIGHT: Final[str] = "ColorLogic_Light"
    FILTER: Final[str] = "Filter"
    HEATER: Final[str] = "Heater"
    HEATER_EQUIP: Final[str] = "Heater_Equipment"
    PUMP: Final[str] = "Pump"
    RELAY: Final[str] = "Relay"
    SENSOR: Final[str] = "Sensor"
    VALVE_ACTUATOR: Final[str] = "ValveActuator"
    VIRT_HEATER: Final[str] = "VirtualHeater"


OMNI_TO_HASS_TYPES: dict[str, str] = {
    OmniTypes.BACKYARD: "device",
    OmniTypes.BOW: "device",
    OmniTypes.BOW_MSP: "device",
    OmniTypes.CL_LIGHT: "light",
    OmniTypes.FILTER: "switch",
    OmniTypes.HEATER: "water_heater",
    OmniTypes.HEATER_EQUIP: "water_heater",
    OmniTypes.PUMP: "switch",
    OmniTypes.RELAY: "switch",
    OmniTypes.SENSOR: "sensor",
    OmniTypes.VALVE_ACTUATOR: "switch",
    OmniTypes.VIRT_HEATER: "water_heater",
}

OMNI_TYPES = [k.value for k in OmniTypes]
OMNI_TYPES_BOW = [OmniModels.BOW_POOL, OmniModels.BOW_SPA]
OMNI_TYPES_PUMP = [OmniTypes.FILTER, OmniTypes.PUMP]
OMNI_TYPES_LIGHT: Final[list[str]] = [k for k, v in OMNI_TO_HASS_TYPES.items() if v == "light"]
OMNI_TYPES_SWITCH: Final[list[str]] = [k for k, v in OMNI_TO_HASS_TYPES.items() if v == "switch"]
OMNI_TYPES_SENSOR: Final[list[str]] = [k for k, v in OMNI_TO_HASS_TYPES.items() if v == "sensor"]
OMNI_TYPES_WATER_HEATER: Final[list[str]] = [k for k, v in OMNI_TO_HASS_TYPES.items() if v == "water_heater"]
