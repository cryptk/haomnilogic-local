"""Constants for the OmniLogic Local integration."""

DOMAIN = "omnilogic_local"
KEY_COORDINATOR = "coordinator"
KEY_OMNI_API = "omni_api"
KEY_DEVICE_REGISTRY = "device_registry"
DEFAULT_POLL_INTERVAL = 20

# According to Hayward docs, the backyard always has a system id of 0
BACKYARD_SYSTEM_ID = 0

UNIQUE_ID = "omnilogic"
MANUFACTURER = "Hayward"

KEY_MSP_BACKYARD = "Backyard"
KEY_MSP_BOW = "Body-of-water"
KEY_MSP_SYSTEM_ID = "System-Id"

KEY_TELEMETRY_BOW = "BodyOfWater"
KEY_TELEMETRY_SYSTEM_ID = "@systemId"

OMNI_BOW_TYPE_POOL = "BOW_POOL"
OMNI_BOW_TYPE_SPA = "BOW_SPA"
OMNI_BOW_TYPES = [
    OMNI_BOW_TYPE_POOL,
    OMNI_BOW_TYPE_SPA
]

OMNI_DEVICE_TYPES_FILTER = [
    "Filter",
]

OMNI_DEVICE_TYPES_LIGHT = [
    "ColorLogic-Light",
]

OMNI_DEVICE_TYPES_SWITCH = [
    "ValveActuator",
    "Relay",
]

OMNI_DEVICE_TYPES_SENSOR = ["Sensor"]

OMNI_DEVICE_TYPES_WATER_HEATER = ["Heater", "Heater-Equipment", "VirtualHeater"]


OMNI_DEVICE_TYPES = [
    KEY_MSP_BACKYARD,
    KEY_MSP_BOW,
    KEY_TELEMETRY_BOW,
    *OMNI_DEVICE_TYPES_FILTER,
    *OMNI_DEVICE_TYPES_LIGHT,
    *OMNI_DEVICE_TYPES_SWITCH,
    *OMNI_DEVICE_TYPES_SENSOR,
    *OMNI_DEVICE_TYPES_WATER_HEATER,
]

OMNI_TO_HASS_TYPES = {
    "Backyard": "device",
    "Body-of-water": "device",
    "Filter": "switch",
    "ColorLogic-Light": "light",
    "ValveActuator": "switch",
    "Relay": "switch",
    "Sensor": "sensor",
    "Heater": "water_heater",
    "Heater-Equipment": "water_heater",
    "VirtualHeater": "water_heater",
}


class OmniModels:
    RELAY_VALVE_ACTUATOR = "RLY_VALVE_ACTUATOR"
    VARIABLE_SPEED_PUMP = "FMT_VARIABLE_SPEED_PUMP"


class OmniTypes:
    FILTER = "Filter"
    RELAY = "Relay"
